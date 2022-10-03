import collections
import logging

from .links import WikiLink


log = logging.getLogger('wikipedia.parser.wikitext')


class WikiText(str):

    def __new__(cls, s=None, *lines):
        lines = list(lines)
        if isinstance(s, str):
            # If s is a single line
            lines.insert(0, s)
        elif isinstance(s, collections.abc.Iterable):
            # if s is iterable of lines
            lines[:0] = s
        return super().__new__(cls, '\n'.join(lines))

    @property
    def links(self):
        yield from WikiLink.find_all(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


class WikitextIterator:

    def __init__(self, wikitext, strip=False, empty=True):
        # NOTE: Using deque() so we can push back part of line and parse as new line
        self.strip = strip
        self.empty = empty
        self.lines = collections.deque(
            wikitext.splitlines()
        )
        self.lines.reverse()

    def push(self, *lines):
        for line in reversed(lines):
            self.lines.append(line)

    def __iter__(self):
        while self.lines:
            line = self.lines.pop()
            if self.strip:
                line = line.strip()
            if (not self.empty) and (not line):
                continue
            yield line

