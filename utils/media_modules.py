"""
Upload modules for images stored by the media worker (mulearn-media-worker).

Each module name is what the frontend sends to the worker as `module`, and the
folder is where the worker stores that module's images in R2. Keys the backend
accepts for a module must start with that folder (see utils/media_keys.py).

Keep this in sync with MEDIA_MODULES in the worker's wrangler.toml: the module
names and folders must match exactly. Size and dimension limits are enforced by
the worker only, so they are not listed here.
"""

# module name -> R2 folder (no leading or trailing slash)
MEDIA_MODULES = {
    "ig_cover": "interest_group/cover",
    "ig_icon": "interest_group/icon",
}
