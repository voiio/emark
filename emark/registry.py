from django.urls import reverse_lazy


class EmarkRegistry:
    def __init__(self):
        self.emails = {}

    def __iter__(self):
        return iter(self.emails.values())

    def __call__(self, email_class):
        self.emails[email_class.__name__] = {
            "app_label": email_class.__module__.split(".")[0],
            "class": email_class,
            "name": email_class.__name__,
            "doc": email_class.__doc__ or "",
            "detail_url": reverse_lazy(
                "emark:email-preview", args=[email_class.__name__]
            ),
        }
        return email_class

    def __getitem__(self, email_class):
        email = self.emails.get(email_class)
        email["preview"] = email["class"].render_preview()
        return email

    def get(self, email_class):
        return self.__getitem__(email_class)


emark_registry = EmarkRegistry()
