import pytest
from fastapi.testclient import TestClient
from autodataset.api.main import app

client = TestClient(app)
auth_headers = {"Authorization": "Bearer valid_token"}

def get_spec_payload():
    return {
        "spec_id": "test_spec_api",
        "domain": "finance",
        "task_type": "classification",
        "target_variable": "target",
        "dataset_size": 100,
        "quality_thresholds": {
            "min_completeness": 0.8,
            "min_consistency": 0.8,
            "min_accuracy": 0.8,
            "max_anomaly_rate": 0.1
        },
        "data_sources": [{
            "source_id": "src1",
            "source_type": "web",
            "location": "http://example.com",
            "format": "csv"
        }],
        "created_by": "api_test"
    }

def test_property_33_api_specification_crud():
    """
    Feature: autodataset-platform, Property 33: API Specification CRUD Operations
    """
    # Create
    payload = get_spec_payload()
    resp_create = client.post("/api/v1/specifications", json=payload, headers=auth_headers)
    assert resp_create.status_code == 201
    
    # Retrieve
    resp_get = client.get(f"/api/v1/specifications/{payload['spec_id']}", headers=auth_headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["domain"] == "finance"
    
    # Update
    payload["domain"] = "healthcare"
    resp_update = client.put(f"/api/v1/specifications/{payload['spec_id']}", json=payload, headers=auth_headers)
    assert resp_update.status_code == 200
    assert resp_update.json()["domain"] == "healthcare"
    
    # Delete
    resp_delete = client.delete(f"/api/v1/specifications/{payload['spec_id']}", headers=auth_headers)
    assert resp_delete.status_code == 204

def test_property_34_api_dataset_retrieval():
    """
    Feature: autodataset-platform, Property 34: API Dataset Retrieval
    """
    resp = client.get("/api/v1/datasets/v123", headers=auth_headers)
    assert resp.status_code == 200
    assert "version_id" in resp.json()

def test_property_35_api_error_response():
    """
    Feature: autodataset-platform, Property 35: API Error Response Correctness
    """
    # Malformed payload (missing required field: task_type)
    bad_payload = get_spec_payload()
    del bad_payload["task_type"]
    resp = client.post("/api/v1/specifications", json=bad_payload, headers=auth_headers)
    assert resp.status_code == 422 # FastAPI validation default
    assert "detail" in resp.json()
    assert any("task_type" in str(e) for e in resp.json()["detail"])

def test_property_36_api_authentication():
    """
    Feature: autodataset-platform, Property 36: API Authentication Enforcement
    """
    resp = client.get("/api/v1/datasets")
    assert resp.status_code == 403 # Missing auth
    
    resp_invalid = client.get("/api/v1/datasets", headers={"Authorization": "Bearer invalid_token"})
    assert resp_invalid.status_code == 401 # Invalid auth
    
    resp_valid = client.get("/api/v1/datasets", headers=auth_headers)
    assert resp_valid.status_code == 200 # Valid auth
