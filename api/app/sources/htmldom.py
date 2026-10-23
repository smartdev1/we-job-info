"""A small, dependency-free HTML DOM built on the standard library.

The connectors need structure-aware parsing (label/value pairs, section
blocks, link targets), and the project standard forbids regex for that:
regexes on these pages break as soon as the site reorders a class name.
``beautifulsoup4``/``lxml`` are the documented target stack but adding a
dependency is a decision for the project owner, so this module provides the
subset of a DOM the extractors actually need until then.

It is deliberately small: no CSS selector engine, no namespace support, no
entity table beyond what ``html.parser`` already resolves.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

# Elements that never have a closing tag.
VOID_TAGS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)

# Elements whose content is not page text.
NON_TEXT_TAGS = frozenset({"script", "style", "noscript", "template", "svg"})

# Elements that start a new line of visible text.
BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
        "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1",
        "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav",
        "ol", "p", "pre", "section", "table", "tbody", "td", "tfoot", "th",
        "thead", "tr", "ul",
    }
)

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse whitespace and strip the result."""
    return _WHITESPACE.sub(" ", text).strip()


class Node:
    """One element of the parsed tree."""

    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None") -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list["Node | str"] = []
        self.parent = parent

    # -- attributes ---------------------------------------------------------
    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def has_class(self, name: str) -> bool:
        return name in self.classes

    @property
    def href(self) -> str | None:
        return self.attrs.get("href")

    # -- content ------------------------------------------------------------
    def text(self) -> str:
        """Visible text of the element and its descendants."""
        parts: list[str] = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return normalize_text(" ".join(parts))

    def raw_text(self) -> str:
        """Visible text with the block boundaries kept as newlines."""
        parts: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                parts.append(child.raw_text())
                if child.tag in BLOCK_TAGS:
                    parts.append("\n")
        return "".join(parts)

    def blocks(self) -> list["Node"]:
        """Direct and indirect block-level children, in document order."""
        found: list[Node] = []
        for child in self.children:
            if isinstance(child, str):
                continue
            if child.tag in BLOCK_TAGS:
                found.append(child)
            found.extend(child.blocks())
        return found

    def lines(self) -> list[str]:
        """Visible text split on block boundaries, empty lines removed."""
        out: list[str] = []
        for line in self.raw_text().split("\n"):
            cleaned = normalize_text(line)
            if cleaned:
                out.append(cleaned)
        return out

    # -- traversal ----------------------------------------------------------
    def walk(self):
        """Yield every descendant element."""
        for child in self.children:
            if isinstance(child, str):
                continue
            yield child
            yield from child.walk()

    def find_all(
        self,
        *,
        tag: str | None = None,
        cls: str | None = None,
        id: str | None = None,
        attrs: dict[str, str] | None = None,
    ) -> list["Node"]:
        """Return the descendants matching every given criterion."""
        out: list[Node] = []
        for node in self.walk():
            if tag is not None and node.tag != tag:
                continue
            if cls is not None and not node.has_class(cls):
                continue
            if id is not None and node.attrs.get("id") != id:
                continue
            if attrs:
                if any(node.attrs.get(k) != v for k, v in attrs.items()):
                    continue
            out.append(node)
        return out

    def find(
        self,
        *,
        tag: str | None = None,
        cls: str | None = None,
        id: str | None = None,
        attrs: dict[str, str] | None = None,
    ) -> "Node | None":
        """Return the first descendant matching every given criterion."""
        matches = self.find_all(tag=tag, cls=cls, id=id, attrs=attrs)
        return matches[0] if matches else None

    def find_by_class_prefix(self, prefix: str) -> list["Node"]:
        """Return the descendants whose class list starts with ``prefix``."""
        return [n for n in self.walk() if any(c.startswith(prefix) for c in n.classes)]

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        cls = self.attrs.get("class", "")
        return f"<{self.tag}{' ' + cls if cls else ''}>"


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("[document]", {}, None)
        self.stack: list[Node] = [self.root]
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in NON_TEXT_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs) -> None:
        if self._skip_depth or tag in NON_TEXT_TAGS:
            return
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        if tag in NON_TEXT_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data.strip():
            return
        self.stack[-1].children.append(data)


def parse(html: str) -> Node:
    """Parse an HTML document and return its root node."""
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return builder.root


def text_of(html: str) -> str:
    """Visible text of a whole document."""
    return parse(html).text()
