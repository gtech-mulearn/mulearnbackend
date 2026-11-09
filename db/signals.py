"""Model-level signals owned by the db layer."""
from django.dispatch import Signal

# Sent by User.save() after an EXISTING user's email changed (spec A §3.1).
# kwargs: user, old_email, new_email, old_was_verified (bool),
# verified_via (str | None: set when the save also proved the new email).
user_email_changed = Signal()
