import logging
import re


log = logging.getLogger('wikipedia.parser.links')


# https://en.wikipedia.org/wiki/Help:Link

WIKI_LINK_START = '[['
WIKI_LINK_END = ']]'

WIKI_LINK_PATTERN = re.compile(
    '\[\[' +
        '(?P<title>[^#|\]]+)?' +
        '(?:#(?P<anchor>[^|\]]+))?' +
        '(?:\|(?P<label>[^\]]+))?' +
    '\]\]'
)


class WikiLink:

    def __init__(self, title=None, anchor=None, label=None):
        self.title = title
        self.anchor = anchor
        # TODO: https://en.wikipedia.org/wiki/Help:Pipe_trick
        self.label = label

    @property
    def target(self):
        if self.anchor:
            return f'{self.title or ""}#{self.anchor}'
        else:
            return self.title

    @property
    def text(self):
        return self.label or self.target

    @classmethod
    def parse(cls, wikitext):
        match = WIKI_LINK_PATTERN.match(wikitext)
        if match:
            return WikiLink(**match.groupdict())

    @classmethod
    def find_all(cls, wikitext):
        for match in WIKI_LINK_PATTERN.finditer(wikitext):
            yield WikiLink(**match.groupdict())

    def __repr__(self):
        if self.label:
            return f'<{self.__class__.__name__} target="{self.target}", label="{self.label}>'
        else:
            return f'<{self.__class__.__name__} target="{self.target}">'

