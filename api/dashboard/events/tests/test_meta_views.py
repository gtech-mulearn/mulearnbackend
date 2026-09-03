import pytest
from rest_framework.test import APIClient
from db.events import Event

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_event_types_scopes_api(api_client):
    """
    Verify that EventTypesScopesAPI returns valid event_type labels without underscores,
    leaves values intact, and returns HTTP 200.
    """
    resp = api_client.get("/api/v1/dashboard/events/meta/event-type-scope/")
    
    assert resp.status_code == 200
    data = resp.json()
    
    assert "response" in data
    assert "event_type" in data["response"]
    
    event_types = data["response"]["event_type"]
    assert len(event_types) > 0
    
    # Build dictionary of original labels for comparison
    original_type_map = dict(zip(Event.EventType.values, Event.EventType.labels))
    
    for item in event_types:
        val = item["value"]
        lbl = item["label"]
        
        # Values must remain unchanged and exist in originals
        assert val in original_type_map, f"Value {val} not found in model choices"
        
        # Labels should not contain underscores
        assert "_" not in lbl, f"Label {lbl} should not contain underscores"
        
        # Label should exactly match original
        expected_label = original_type_map[val]
        assert lbl == expected_label, f"Expected label '{expected_label}', got '{lbl}'"
