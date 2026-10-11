import logging
import threading

import requests

from coordination import CURRENT


logger = logging.getLogger(__name__)


class Synchronizer:
    def __init__(self, coordinator, store, token, peer_urls):
        self.coordinator = coordinator
        self.store = store
        self.headers = {"X-Cluster-Token": token}
        self.peer_urls = set(peer_urls)
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.sync_lock = threading.Lock()
        self.thread = None
        self.last_error = None

    def start(self):
        self.coordinator.zk.DataWatch(
            CURRENT, func=self.changed
        )
        self.thread = threading.Thread(
            target=self.run,
            daemon=True,
        )
        self.thread.start()

    def changed(self, data, stat, event=None):
        self.wake.set()
        return not self.stopping.is_set()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=15)

    def synchronize(self):
        with self.sync_lock:
            metadata, _ = self.coordinator.current()
            version = metadata.get("version")
            if not version:
                return

            if not self.store.path(version).exists():
                sources = list(metadata.get("sources", []))
                sources.extend(
                    member["url"]
                    for member in self.coordinator.members()
                )
                downloaded = False
                for url in dict.fromkeys(sources):
                    if url not in self.peer_urls:
                        continue
                    if url == self.coordinator.server_url:
                        continue
                    try:
                        response = requests.get(
                            url + "/internal/models/" + version,
                            headers=self.headers,
                            timeout=10,
                        )
                        response.raise_for_status()
                        self.store.save_bytes(
                            version, response.content
                        )
                        downloaded = True
                        break
                    except Exception as error:
                        logger.warning(
                            "Preuzimanje sa %s nije uspelo: %s",
                            url, error,
                        )
                if not downloaded:
                    raise RuntimeError(
                        "Nijedan server nije poslao trazeni model."
                    )

            latest, _ = self.coordinator.current()
            if latest.get("version") == version:
                self.store.activate(version)

    def run(self):
        while not self.stopping.is_set():
            try:
                self.coordinator.register()
                self.synchronize()
                self.last_error = None
            except Exception as error:
                self.last_error = str(error)
                logger.warning(
                    "Sinhronizacija nije zavrsena: %s", error
                )
            self.wake.wait(timeout=2)
            self.wake.clear()
