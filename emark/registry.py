"""This module is used to register the email classes for the emark dashboard.

The following is an example of how to use this module:

    ```python
    from emark.registry import emark_registry
    from emark.emails import EAPExpertBookingEmail, EAPExpertBookingTicketEmail

    @emark_registry
    class EAPExpertBookingEmail(MarkdownEmail):
        template = "experts/emails/booking.md"

    @emark_registry
    class EAPExpertBookingTicketEmail(EAPSupportTicketEmail):
        template = "experts/emails/booking_ticket.md"
    ```
"""

registry = {}


def emark_registry(cls, key=None):
    """Decorator to register an email class with the emark dashboard.

    Args:
        cls (class): The email
        key (str): The key to use in the registry. Defaults to the class name.

    Returns:
        class: The class that was passed in.
    """
    if key is None:
        key = cls.__name__

    registry[key] = {
        "app_label": cls.__module__.split(".")[0],
        "name": key,
        "cls": cls,
    }

    return cls
