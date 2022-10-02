from __future__ import annotations

import dataclasses
import re
from html.parser import HTMLParser
from typing import Dict

__all__ = ["HTML2TextParser"]


@dataclasses.dataclass
class Node:
    """
    Simple HTML node that can be extracted into plain text.

    Nodes have a parent and children link to create a tree structure.
    Plain text extraction is done by recursively traversing the tree.
    """

    name: str
    parent: Node | None
    attrs: Dict[str:str] = dataclasses.field(default_factory=dict)
    children: list[Node | str] = dataclasses.field(init=False, default_factory=list)

    def __post_init__(self):
        if self.parent:
            self.parent.children.append(self)

    def __iter__(self) -> Node | str:
        yield from self.children

    def __repr__(self) -> str:
        html_attrs = " ".join(f'{k}="{v}"' for k, v in self.attrs.items())
        if html_attrs:
            return f"<{self.name} {html_attrs}/>"
        return f"<{self.name}/>"

    def __str__(self) -> str:
        match self.name:
            case "br":
                return "\n"
            case "hr":
                return f"\n{'-' * 50}\n"
            case "a":
                if self.text:
                    return f"{self.text} <{self.attrs['href']}>"
            case "p" | "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "table" | "tr" | "div":
                return f"{self.text}\n\n"
            case "em" | "strong" | "i" | "b" | "u" | "code":
                return f"*{self.text}*"
            case "img":
                if "alt" in self.attrs:
                    return f"[image: {self.attrs['alt']}]"
            case "script" | "style" | "title":
                return ""
            case _:
                return self.text

    @property
    def text(self) -> str:
        text = ""
        for child in self.children:
            if isinstance(child, str):
                lines = child.split("\n")
                text += " ".join(lines)
            else:
                text += str(child)
        return text


class HTML2TextParser(HTMLParser):
    """Extract plain text from HTML emails, similar to Gmail."""

    DOUBLE_NEWLINE = re.compile(r"\n{3,}")  # 3 or more newlines
    DOUBLE_SPACE = re.compile(r" {2,}")  # 2 or more spaces

    START_END_TAGS = [  # elements that don't need to be closed in HTML
        "area",
        "base",
        "br",
        "col",
        "command",
        "embed",
        "hr",
        "img",
        "input",
        "keygen",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]

    def __init__(self):
        self.root = None
        super().__init__()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Walk up the tree."""
        if tag in self.START_END_TAGS:
            # HTML doesn't require leave elements to be closed, like <img>
            self.handle_startendtag(tag, attrs)
        else:
            self.root = Node(tag.lower(), dict(attrs), self.root)

    def handle_endtag(self, tag: str) -> None:
        """Walk down the tree."""
        self.root = self.root.parent or self.root

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Add a leave node."""
        Node(tag.lower(), dict(attrs), self.root)

    def handle_data(self, data: str) -> None:
        """Add text as a leave to the current node."""
        if self.root:
            self.root.children.append(data)

    @classmethod
    def from_html(cls, html: str) -> HTML2TextParser:
        """Parse HTML and return a HTML2TextParser instance.
        >>> HTML2TextParser.from_html(html).text
        """
        parser = cls()
        parser.feed(html)
        return parser

    @classmethod
    def to_text(cls, html: str) -> str:
        """Parse HTML and return plain text. Similar to Gmail.
        >>> HTML2TextParser.to_text(html)
        """
        return str(cls.from_html(html))

    @classmethod
    def from_file(cls, path: str) -> HTML2TextParser:
        """Parse HTML from a file and return a HTML2TextParser instance.
        >>> HTML2TextParser.from_file(path).text
        """
        with open(path, "r") as file:
            return cls.from_html(file.read())

    @classmethod
    def from_url(cls, url: str) -> HTML2TextParser:
        """Parse HTML from a URL and return a HTML2TextParser instance. Requires requests.
        >>> HTML2TextParser.from_url(url).text
        """
        import requests

        return cls.from_html(requests.get(url).text)

    @classmethod
    def from_email(cls, email: str) -> HTML2TextParser:
        """Parse HTML from an email and return a HTML2TextParser instance. Requires email.
        >>> HTML2TextParser.from_email(email).text
        """
        import email

        message = email.message_from_string(email)
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    return cls.from_html(part.get_payload())
        else:
            return cls.from_html(message.get_payload())

    @classmethod
    def from_bytes(cls, data: bytes) -> HTML2TextParser:
        """Parse HTML from bytes and return a HTML2TextParser instance.
        >>> HTML2TextParser.from_bytes(data).text
        """
        return cls.from_html(data.decode())

    def __hash__(self) -> int:
        """Return a hash value for the parser."""
        return hash(self.text)

    def __eq__(self, other: object) -> bool:
        """Return True if the parsers are equal."""
        if isinstance(other, HTML2TextParser):
            return self.text == other.text
        return False

    def __str__(self) -> str:
        # remove leading/trailing whitespace
        lines = str(self.root).strip().split("\n")
        text = "\n".join(line.strip() for line in lines)
        # sanitize all wide vertical or horizontal spaces
        text = self.DOUBLE_NEWLINE.sub("\n\n", text.strip())
        return self.DOUBLE_SPACE.sub(" ", text)
