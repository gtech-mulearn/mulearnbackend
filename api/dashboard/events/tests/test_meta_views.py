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
    expected_type_descriptions = {
        'HACKATHON': 'An intensive, collaborative coding event focused on building software projects.',
        'WORKSHOP': 'An interactive, hands-on session focusing on learning specific skills or techniques.',
        'WEBINAR': 'An online educational presentation or seminar.',
        'SEMINAR': 'A formal presentation or educational session on a specific topic.',
        'BOOTCAMP': 'A short, intensive training program designed to teach practical skills quickly.',
        'MEETUP': 'An informal gathering of individuals with a shared interest or profession.',
        'CONFERENCE': 'A formal meeting for discussion and presentations within a specific field.',
        'COMPETITION': 'An event where individuals or teams compete against each other for a prize.',
        'IDEATHON': 'A short, intensive brainstorming event that focuses on generating new ideas.',
        'CULTURAL_EVENT': 'An event celebrating arts, music, or other cultural activities.',
        'SPORTS_EVENT': 'An athletic competition or physical activity event.',
        'COMMUNITY_EVENT': 'A gathering or activity designed to bring the community together.',
        'EXPO': 'A large-scale exhibition showcasing products, services, or innovations.',
        'NETWORKING_EVENT': 'A gathering specifically designed for professionals to connect and build relationships.',
        'TECH_TALK': 'A concise presentation on a technical topic, tool, or innovation.',
        'OTHERS': 'Any event that does not fit into the standard categories.',
    }
    for item in event_types:
        val = item["value"]
        lbl = item["label"]
        desc = item.get("description")
        # Values must remain unchanged and exist in originals
        assert val in original_type_map, f"Value {val} not found in model choices"
        # Labels should not contain underscores
        assert "_" not in lbl, f"Label {lbl} should not contain underscores"
        # Label should exactly match original
        expected_label = original_type_map[val]
        assert lbl == expected_label, f"Expected label '{expected_label}', got '{lbl}'"
        assert desc == expected_type_descriptions.get(val, "")
    assert "event_scope" in data["response"]
    event_scopes = data["response"]["event_scope"]
    assert len(event_scopes) > 0
    original_scope_map = dict(zip(Event.EventScope.values, Event.EventScope.labels))
    expected_descriptions = {
        'MAKER': 'Events focused on hardware, electronics, and physical prototyping.',
        'CODER': 'Events focused on software development and programming.',
        'MANAGER': 'Events focused on leadership, product management, and business.',
        'CREATIVE': 'Events focused on design, digital art, and creative media.',
    }
    for item in event_scopes:
        val = item["value"]
        lbl = item["label"]
        desc = item.get("description")
        assert val in original_scope_map
        assert lbl == original_scope_map[val]
        assert desc == expected_descriptions.get(val, "")
