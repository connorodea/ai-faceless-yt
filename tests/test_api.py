from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.abspath("."))
import ai_faceless.api as api

client = TestClient(api.app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_generate_endpoint(monkeypatch):
    called = {}
    def fake_run_pipeline(config_path="config.yaml"):
        called['ran'] = True
    monkeypatch.setattr(api, "run_pipeline", fake_run_pipeline)
    resp = client.post("/generate", json={"script": "hello"})
    assert resp.status_code == 200
    assert called.get('ran')
