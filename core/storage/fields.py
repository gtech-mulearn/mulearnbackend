from stdimage.models import StdImageField
from core.storage import PublicStorage, MediaStorage


class ResizedImageField(StdImageField):
    def __init__(self, *args, **kwargs):
        is_public = kwargs.get("is_public", False)

        if is_public:
            kwargs.setdefault("storage", PublicStorage())
        else:
            kwargs.setdefault("storage", MediaStorage())

        kwargs.setdefault(
            "variations",
            {
                "thumbnail": {"width": 100, "height": 100, "crop": False},
                "medium": {"width": 600, "height": 600, "crop": False},
            },
        )
        super().__init__(*args, **kwargs)
