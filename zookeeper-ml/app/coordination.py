import json
import threading

from kazoo.client import KazooClient


ROOT = "/wine-ml"
SERVERS = ROOT + "/servers"
CURRENT = ROOT + "/current"


class Coordinator:
    def __init__(self, hosts, server_id, server_url):
        self.zk = KazooClient(hosts=hosts)
        self.server_id = server_id
        self.server_url = server_url
        self.node = None
        self.registration_lock = threading.Lock()

    def start(self):
        self.zk.start(timeout=30)
        self.zk.ensure_path(SERVERS)
        self.zk.ensure_path(CURRENT)
        self.register()

    def stop(self):
        self.zk.stop()
        self.zk.close()

    def register(self):
        if not self.zk.connected:
            raise RuntimeError("ZooKeeper nije dostupan.")
        with self.registration_lock:
            if self.node and self.zk.exists(self.node):
                return self.node
            data = json.dumps({
                "id": self.server_id,
                "url": self.server_url,
            }).encode()
            self.node = self.zk.create(
                SERVERS + "/server-",
                data,
                ephemeral=True,
                sequence=True,
            )
            return self.node

    def members(self):
        result = []
        for name in sorted(self.zk.get_children(SERVERS)):
            path = SERVERS + "/" + name
            try:
                data, _ = self.zk.get(path)
                member = json.loads(data)
                member["node"] = path
                result.append(member)
            except Exception:
                if self.zk.exists(path):
                    raise
        return result

    def leader(self):
        members = self.members()
        if not members:
            raise RuntimeError("Nema dostupnih servera.")
        return members[0]

    def current(self):
        data, stat = self.zk.get(CURRENT)
        return json.loads(data or b"{}"), stat

    def update_lock(self):
        return self.zk.Lock(
            ROOT + "/update-lock",
            identifier=self.server_id,
        )

    def publish(self, metadata, previous_stat, leader_node):
        if self.leader()["node"] != leader_node:
            raise RuntimeError("Glavni server se promenio.")

        transaction = self.zk.transaction()
        transaction.check(leader_node, version=0)
        transaction.set_data(
            CURRENT,
            json.dumps(metadata).encode(),
            version=previous_stat.version,
        )
        results = transaction.commit()
        for result in results:
            if isinstance(result, Exception):
                raise result
