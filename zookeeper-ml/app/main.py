import hmac
import json
import os
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import (
    Depends, FastAPI, File, Header, HTTPException,
    Query, Request, UploadFile,
)
from fastapi.responses import Response

from coordination import Coordinator
from ml import validate_features
from model_store import ModelStore
from synchronization import Synchronizer


TOKEN = os.environ["CLUSTER_TOKEN"]
SERVER_ID = os.environ["SERVER_ID"]
SERVER_URL = os.environ["SERVER_URL"]
PEERS = os.environ["PEER_URLS"].split(",")

store = ModelStore(os.getenv("MODEL_DIR", "/models"))
coordinator = Coordinator(
    os.getenv("ZK_HOSTS", "zookeeper:2181"),
    SERVER_ID,
    SERVER_URL,
)
synchronizer = Synchronizer(
    coordinator, store, TOKEN, PEERS
)


@asynccontextmanager
async def lifespan(app):
    coordinator.start()
    synchronizer.start()
    try:
        yield
    finally:
        synchronizer.stop()
        coordinator.stop()


app = FastAPI(
    title="Distribuirani ML model",
    lifespan=lifespan,
)


def cluster_auth(
    x_cluster_token: str = Header(default="")
):
    if not hmac.compare_digest(x_cluster_token, TOKEN):
        raise HTTPException(403, "Pristup nije dozvoljen.")


def state():
    metadata, _ = coordinator.current()
    version = metadata.get("version")
    return {
        "server": SERVER_ID,
        "leader": coordinator.leader()["id"],
        "current_version": version,
        "local_version": store.active_version,
        "ready": bool(
            coordinator.zk.connected
            and version
            and version == store.active_version
        ),
    }


@app.get("/status")
def status():
    try:
        return state()
    except Exception as error:
        raise HTTPException(503, str(error))


@app.get("/predict", summary="Get - Predict")
def predict(
    parameters: str = Query(
        description="JSON niz objekata sa osobinama vina."
    )
):
    try:
        samples = json.loads(parameters)
        if (
            not isinstance(samples, list)
            or not 1 <= len(samples) <= 1000
            or not all(isinstance(item, dict) for item in samples)
        ):
            raise ValueError(
                "Potrebno je proslediti niz od 1 do 1000 objekata."
            )
        features = validate_features(pd.DataFrame(samples))
    except Exception as error:
        raise HTTPException(400, str(error))

    try:
        metadata, _ = coordinator.current()
        version = metadata.get("version")
        if not version:
            raise RuntimeError("Model jos nije treniran.")
        predictions = store.predict(version, features)
        latest, _ = coordinator.current()
        if latest.get("version") != version:
            raise RuntimeError(
                "Model je promenjen. Ponovite zahtev."
            )
        return {
            "server": SERVER_ID,
            "version": version,
            "predictions": predictions,
        }
    except Exception as error:
        raise HTTPException(503, str(error))


@app.get(
    "/internal/models/{version}",
    dependencies=[Depends(cluster_auth)],
    include_in_schema=False,
)
def download_model(version: str):
    try:
        return Response(
            store.read_bytes(version),
            media_type="application/octet-stream",
        )
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "Model nije pronadjen.")


@app.put(
    "/internal/models/{version}",
    dependencies=[Depends(cluster_auth)],
    include_in_schema=False,
)
async def receive_model(version: str, request: Request):
    data = await request.body()
    if not data or len(data) > 20 * 1024 * 1024:
        raise HTTPException(400, "Neispravna velicina modela.")
    try:
        store.save_bytes(version, data)
        return {"stored_version": version}
    except ValueError as error:
        raise HTTPException(400, str(error))


@app.post(
    "/internal/synchronize",
    dependencies=[Depends(cluster_auth)],
    include_in_schema=False,
)
def synchronize_now():
    try:
        synchronizer.synchronize()
        return state()
    except Exception as error:
        raise HTTPException(503, str(error))


@app.put("/model", summary="Put - Update model")
def update_model(
    file: UploadFile = File(...),
    x_forwarded_update: str = Header(default=""),
):
    import requests
    from ml import train_csv

    data = file.file.read(10 * 1024 * 1024 + 1)
    if not data or len(data) > 10 * 1024 * 1024:
        raise HTTPException(
            400, "CSV mora biti neprazan i najvise 10 MB."
        )

    try:
        coordinator.register()
        leader = coordinator.leader()
        if leader["url"] not in PEERS:
            raise RuntimeError("Nepoznata adresa glavnog servera.")
    except Exception as error:
        raise HTTPException(503, str(error))

    if leader["node"] != coordinator.node:
        if x_forwarded_update:
            raise HTTPException(
                503, "Glavni server se promenio. Ponovite zahtev."
            )
        try:
            response = requests.put(
                leader["url"] + "/model",
                files={
                    "file": (
                        file.filename or "training.csv",
                        data,
                        "text/csv",
                    )
                },
                headers={"X-Forwarded-Update": "1"},
                timeout=600,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type="application/json",
            )
        except requests.RequestException as error:
            raise HTTPException(503, str(error))

    lock = coordinator.update_lock()
    try:
        acquired = lock.acquire(timeout=10)
    except Exception as error:
        raise HTTPException(503, str(error))
    if not acquired:
        raise HTTPException(
            409, "Drugo azuriranje je u toku. Pokusajte kasnije."
        )

    committed = False
    version = None
    try:
        leader_node = coordinator.node
        if coordinator.leader()["node"] != leader_node:
            raise RuntimeError("Glavni server se promenio.")

        _, previous_stat = coordinator.current()
        try:
            model, rows = train_csv(data)
        except ValueError as error:
            raise HTTPException(400, str(error))

        version = store.save_model(model)
        model_data = store.read_bytes(version)
        members = coordinator.members()
        headers = {"X-Cluster-Token": TOKEN}

        for member in members:
            url = member["url"]
            if url not in PEERS:
                raise RuntimeError("Nepoznata adresa servera.")
            if url == SERVER_URL:
                continue
            response = requests.put(
                url + "/internal/models/" + version,
                data=model_data,
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            if response.json().get("stored_version") != version:
                raise RuntimeError(
                    "Server nije potvrdio cuvanje modela."
                )

        coordinator.publish(
            {
                "version": version,
                "sources": [member["url"] for member in members],
                "trained_by": SERVER_ID,
                "training_rows": rows,
            },
            previous_stat,
            leader_node,
        )
        committed = True
        synchronizer.synchronize()

        targets = {
            member["url"]: member
            for member in members + coordinator.members()
        }
        confirmed = []
        for url, member in targets.items():
            if url not in PEERS:
                raise RuntimeError("Nepoznata adresa servera.")
            if url == SERVER_URL:
                result = state()
            else:
                response = requests.post(
                    url + "/internal/synchronize",
                    headers=headers,
                    timeout=20,
                )
                response.raise_for_status()
                result = response.json()
            if (
                result.get("local_version") != version
                or not result.get("ready")
            ):
                raise RuntimeError(
                    "Server nije potvrdio aktiviranje modela."
                )
            confirmed.append(member["id"])

        return {
            "version": version,
            "trained_by": SERVER_ID,
            "training_rows": rows,
            "synchronized_servers": confirmed,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            503,
            {
                "message": str(error),
                "version": version,
                "committed": committed,
            },
        )
    finally:
        lock.release()
