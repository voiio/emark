from __future__ import annotations

import dataclasses
import re
from html.parser import HTMLParser

__all__ = ["HTML2TextParser"]


@dataclasses.dataclass
class Node:
    """
    Simple HTML node that can be extracted into plain text.

    Nodes have a parent and children link to create a tree structure.
    Plain text extraction is done by recursively traversing the tree.
    """

    name: str
    attrs: {str: str}
    parent: Node | None
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
        return f"{self.text}"

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

    def __str__(self) -> str:
        # remove leading/trailing whitespace
        lines = str(self.root).strip().split("\n")
        text = "\n".join(line.strip().strip("\ufeff") for line in lines)
        # sanitize all wide vertical or horizontal spaces
        text = self.DOUBLE_NEWLINE.sub("\n\n", text.strip())
        return self.DOUBLE_SPACE.sub(" ", text)
