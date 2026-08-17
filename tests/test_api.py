import importlib
import os
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, os.path.abspath("."))


def make_client(monkeypatch, api_key=None):
    if api_key is not None:
        monkeypatch.setenv("API_KEY", api_key)
    else:
        monkeypatch.delenv("API_KEY", raising=False)
    import ai_faceless.api as api_mod
    importlib.reload(api_mod)
    client = TestClient(api_mod.app)
    return client, api_mod


def test_health_endpoint(monkeypatch):
    client, _ = make_client(monkeypatch)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_generate_endpoint(monkeypatch):
    client, api_mod = make_client(monkeypatch)
    called = {}

    def fake_run_pipeline(config_path="config.yaml"):
        called['ran'] = True
    monkeypatch.setattr(api_mod, "run_pipeline", fake_run_pipeline)
    resp = client.post("/generate", json={"script": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert called.get('ran')
    status = client.get(f"/job/{data['job_id']}").json()
    assert status["status"] == "completed"


def test_index_page(monkeypatch):
    client, _ = make_client(monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_generate_form(monkeypatch):
    client, api_mod = make_client(monkeypatch)
    called = {}

    def fake_run_pipeline(config_path="config.yaml"):
        called['ran'] = True
    monkeypatch.setattr(api_mod, "run_pipeline", fake_run_pipeline)
    resp = client.post("/generate-form", data={"script": "hello"})
    assert resp.status_code == 200
    assert "Job submitted" in resp.text
    assert called.get('ran')


def test_api_key_required(monkeypatch):
    client, api_mod = make_client(monkeypatch, api_key="secret")
    monkeypatch.setattr(api_mod, "run_pipeline", lambda **_: None)
    resp = client.post("/generate", json={"script": "hi"})
    assert resp.status_code == 401
    resp = client.post("/generate", json={"script": "hi"}, headers={"X-API-Key": "secret"})
    assert resp.status_code == 200
    assert "job_id" in resp.json()
