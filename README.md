# Django eMark↓

<img alt="emark logo: envelope with markdown stamp" src="https://raw.githubusercontent.com/voiio/emark/main/emark-logo.svg" width="320" height="170" align="right">

Markdown template based HTML and text emails for Django.

* simple email templates with markdown
* support for HTML and text emails
* i18n support
* built-in UTM tracking
* built-in sent, open and click tracking
* automatic CSS inliner via [premailer](https://github.com/peterbe/premailer/)

[![PyPi Version](https://img.shields.io/pypi/v/emark.svg)](https://pypi.python.org/pypi/emark/)
[![Test Coverage](https://codecov.io/gh/voiio/emark/branch/main/graph/badge.svg)](https://codecov.io/gh/voiio/emark)
[![GitHub License](https://img.shields.io/github/license/voiio/emark)](https://raw.githubusercontent.com/voiio/emark/master/LICENSE)

## Setup

```ShellSession
python3 -m pip install emark
```

```python
# settings.py
INSTALLED_APPS = [
    'emark',
    # ...
]
```

```ShellSession
python3 manage.py migrate
```

## Usage

```markdown
<!-- myapp/my_message.md -->
# Hello World

Hi {{ user.short_name }}!
```

```python
# myapp/emails.py
from emark.message import MarkdownEmail

class MyMessage(MarkdownEmail):
    subject = "Hello World"
    template_name = "myapp/my_message.md"
```

```python
# myapp/views.py
from . import emails

def my_view(request):
    message = emails.MyMessage.to_user(request.user)
    message.send()
```

### Templates

You can use Django's template engine, just like you usually would.
You can use translations, template tags, filters, blocks, etc.

You may also have a base template, that you inherit form in your individual
emails to provide a consistent salutation and farewell.

```markdown
<!-- base.md -->
{% load static i18n %}
{% block salutation %}Hi {{ user.short_name }}!{% endblock %}

{% block content %}{% endblock %}

{% block farewell %}
{% blocktrans trimmed %}
Best regards,
{{ site_admin }}
{% endblocktrans %}
{% endblock %}

{% block footer %}
Legal footer.
{% endblock %}
```

```markdown
<!-- myapp/email.md -->
{% extends "base.md" %}

{% block content %}
This is the content of the email.
{% endblock %}
```

### Context

The context is passed to the template as a dictionary. Furthermore, you may
override the `get_context_data` method to add additional context variables.

```python
# myapp/emails.py
from emark.message import MarkdownEmail

class MyMessage(MarkdownEmail):
    subject = "Hello World"
    template_name = "myapp/email.md"

    def get_context_data(self):
        context = super().get_context_data()
        context["my_variable"] = "Hello World"
        return context
```

### Tracking

#### Sent, Open & Click Tracking

Django eMark comes with built-in tracking for sent, open and click events.
The tracking is done via a tracking pixel and a redirect view.

As an added bonus, this feature also comes with an open-in-browser link that
allows the user to view the email in their browser if their email client does
not support HTML emails.

This feature is disabled by default. To enable it, you need to use a separate email
backend. This backend will send the email via SMTP and also add the tracking
pixel and redirect view. However, it will send a separate email for each
recipient, which may not be desirable in all cases.

```python
# settings.py
EMAIL_BACKEND = "emark.backends.TrackingSMTPEmailBackend"
```

Furthermore, you need to add the tracking view to your `urls.py`:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # … other urls
    path("emark/", include("emark.urls")),
]
```

You will need to provide a domain name for the tracking pixel and redirect view.
This can be done via the `DOMAIN` setting:

```python
# settings.py
EMARK = {
    "DOMAIN": "example.com"
}
```

If the site framework is installed and no settings are provided,
the domain will be automatically set to the current site's domain.

The tracking data is stored in the database. You need to run migrations to
create the necessary tables:

```ShellSession
python3 manage.py migrate
```

You can analyze the tracking data via the tables `emark_sent`, `emark_open` and
`emark_click`.

#### UTM Tracking

Every `MarkdownEmail` subclass comes with automatic UTM tracking.
UTM parameters are added to all links in the email. Existing UTM params on link
that have been explicitly set, are not overridden. The default parameters are:

* `utm_source`: `website`
* `utm_medium`: `email`
* `utm_campaign`: `{{ EMAIL_CLASS_NAME }}`

The global UTM parameters can be overridden via the `EMARK_UTM_PARAMS` setting,
which is a dictionary of parameters:

```python
# settings.py
EMARK = {
  "UTM_PARAMS": {
      "utm_source": "website",  # default
      "utm_medium": "email",  # default
  }
}
```

You may also change the UTM parameters by overriding the `get_utm_params`
or passing a `utm_params` dictionary to class constructor.

```python
# myapp/emails.py
from emark.message import MarkdownEmail


class MyMessage(MarkdownEmail):
  subject = "Hello World"
  template_name = "myapp/email.md"

  # override the parameters for this email class
  def get_utm_params(self):
    return {
      "utm_source": "myapp",
      "utm_medium": "email",
      "utm_campaign": "my-campaign",
    }


# or alternatively during instantiation
MyMessage(utm_params={"utm_campaign": "my-other-campaign"}).send()
```

## Development

Pretty HTML emails are great, unless they spam your console during development.
To prevent this, you can use the `ConsoleEmailBackend`:

```python
# settings.py
EMAIL_BACKEND = "emark.backends.ConsoleEmailBackend"
```

The `ConsoleEmailBackend` will only print the plain text version of the email.

## Credits

- Django eMark uses modified version of [Responsive HTML Email Template](https://github.com/leemunroe/responsive-html-email-template/) as a base template
- For CSS inlining, Django eMark uses [premailer](https://github.com/peterbe/premailer/)
