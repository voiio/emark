"""This module is used to register the email classes for the emark dashboard.

The following is an example of how to use this module:

    ```python
    from emark.messages import MarkdownEmail
    from emark.contrib import dashboard

    @dashboard.register
    class MyEmail(MarkdownEmail):
        template = "my_app/emails/my_email.md"

    ```
"""

from emark.message import MarkdownEmail

_registry: dict[str, type[MarkdownEmail]] = {}


__all__ = ["register"]


def register(cls: type[MarkdownEmail], key: str = None) -> type[MarkdownEmail]:
    """Register a MarkdownEmail with the registry."""
    _registry[key or f"{cls.__module__}{cls.__qualname__}"] = cls
    return cls
