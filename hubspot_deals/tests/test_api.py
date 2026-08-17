import pytest
from fastapi.testclient import TestClient
from app import app
import uuid

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()

def test_start_scan_missing_fields():
    response = client.post("/api/v1/scan/start", json={})
    assert response.status_code == 422 # FastAPI validation error

def test_scan_status_not_found():
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/scan/status/{random_id}")
    assert response.status_code == 404

def test_scan_result_not_found():
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/scan/result/{random_id}")
    assert response.status_code == 404

def test_cancel_scan_not_found():
    random_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/scan/cancel/{random_id}")
    assert response.status_code == 404

def test_remove_scan_not_found():
    random_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/scan/remove/{random_id}")
    assert response.status_code == 404
