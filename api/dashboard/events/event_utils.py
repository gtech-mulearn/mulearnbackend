from db.events import Event

def get_event_types_scopes():
    """
    Returns a combined dictionary containing formatted lists of event types and event scopes.
    """
    return {
        "event_type": [val.replace('_', ' ').capitalize() for val in Event.EventType.values],
        "event_scope": [val.replace('_', ' ').capitalize() for val in Event.EventScope.values],
    }
