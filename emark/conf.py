from django.conf import settings

__all__ = ["get_settings"]


def get_settings():
    return type(
        "Settings",
        (),
        {
            "UTM_PARAMS": {"utm_source": "website", "utm_medium": "email"},
            "DOMAIN": None,
            **getattr(settings, "EMARK", {}),
        },
    )
