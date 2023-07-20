import pytest

from tests.test_message import MarkdownEmailTest


@pytest.fixture
def email_message():
    msg = MarkdownEmailTest(
        language="en-US",
        subject="Peanut strikes back",
        context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
        to=["test@example.com"],
    )
    return msg
