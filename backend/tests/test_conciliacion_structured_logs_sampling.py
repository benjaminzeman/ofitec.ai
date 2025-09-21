import os
import uuid
import logging
import random
import math
from pathlib import Path
import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_sampling_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _count_events(caplog, name: str):
    cnt = 0
    for rec in caplog.records:
        msg = rec.getMessage()
        if f'"event": "{name}"' in msg:
            cnt += 1
    return cnt


def test_sampling_probability(client, caplog):
    caplog.set_level(logging.INFO)
    random.seed(12345)
    rate = 0.25
    os.environ["RECON_STRUCTURED_LOG_SAMPLE"] = str(rate)
    N = 120
    for _ in range(N):
        client.post("/api/conciliacion/sugerencias", json={"source_type": "bank"})
    emitted = _count_events(caplog, "recon_suggest_request")
    mean = N * rate
    std = math.sqrt(N * rate * (1 - rate))
    lower = int(mean - 3 * std)
    upper = int(mean + 3 * std)
    assert lower <= emitted <= upper, f"emitted={emitted} outside [{lower},{upper}] (mean={mean:.1f}, std={std:.2f})"
    os.environ.pop("RECON_STRUCTURED_LOG_SAMPLE", None)
