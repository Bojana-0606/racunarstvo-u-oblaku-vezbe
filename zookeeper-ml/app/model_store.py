import hashlib
import io
import os
import re
import tempfile
import threading
from pathlib import Path

import joblib


class ModelStore:
    def __init__(self, directory="/models"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.active_version = None
        self.active_model = None

    def path(self, version):
        if not re.fullmatch(r"[0-9a-f]{64}", version):
            raise ValueError("Neispravna verzija modela.")
        return self.directory / f"{version}.joblib"

    def save_model(self, model):
        buffer = io.BytesIO()
        joblib.dump(model, buffer, compress=3)
        data = buffer.getvalue()
        version = hashlib.sha256(data).hexdigest()
        self.save_bytes(version, data)
        return version

    def save_bytes(self, version, data):
        destination = self.path(version)
        if hashlib.sha256(data).hexdigest() != version:
            raise ValueError("Sadrzaj modela ne odgovara verziji.")

        with self.lock:
            if destination.exists():
                return
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=self.directory, delete=False
                ) as output:
                    temporary = output.name
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, destination)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)

    def read_bytes(self, version):
        return self.path(version).read_bytes()

    def activate(self, version):
        with self.lock:
            if self.active_version == version:
                return
            data = self.read_bytes(version)
            if hashlib.sha256(data).hexdigest() != version:
                raise ValueError("Kopija modela je ostecena.")
            model = joblib.load(io.BytesIO(data))
            self.active_model = model
            self.active_version = version

    def predict(self, version, features):
        with self.lock:
            if self.active_version != version:
                raise RuntimeError("Model jos nije sinhronizovan.")
            return self.active_model.predict(features).tolist()
