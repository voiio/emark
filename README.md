# emark

<img alt="emark logo: envelope with markdown stamp" src="emark-logo.png" width="320" height="170" style="float: right">

Markdown template based HTML and text emails for Django.

* simple email templates with markdown
* support for HTML and text emails
* i18n support
* built-in UTM tracking

[![PyPi Version](https://img.shields.io/pypi/v/emark.svg)](https://pypi.python.org/pypi/emark/)
[![Test Coverage](https://codecov.io/gh/voiio/emark/branch/main/graph/badge.svg)](https://codecov.io/gh/voiio/emark)
[![GitHub License](https://img.shields.io/github/license/voiio/emark)](https://raw.githubusercontent.com/voiio/emark/master/LICENSE)

## Setup

```shell
python3 -m pip install emark
```

```python
# settings.py
INSTALLED_APPS = [
    'emark',
    # ...
]
```

```shell
python3 manage.py migrate
```

## Usage

```markdown
<!-- myapp/email.md -->
# Hello World

Hi {{ user.short_name }}!
```

```python
# myapp/emails.py
from emark.message import MarkdownEmail

class MyMessage(MarkdownEmail):
    subject = "Hello World"
    template_name = "myapp/email.md"


# render and send the email
MyMessage(language="en", to=["peter.parker@avengers.com"]).send()
```
