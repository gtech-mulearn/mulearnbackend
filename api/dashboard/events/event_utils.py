from db.events import Event

def get_event_types_scopes():
    """
    Returns a combined dictionary containing formatted lists of event types and event scopes.
    """
    return {
        "event_type": list(Event.EventType.labels),
        "event_scope": list(Event.EventScope.labels),
    }
