import collections
import functools
import logging
import re

from .wikitext import WikiText, WikitextIterator

from .tables import Table
from .templates import Template
from .lists import List


log = logging.getLogger('wikipedia.parser.sections')


# https://en.wikipedia.org/wiki/Help:Section
# https://meta.wikimedia.org/wiki/Help:Section

MAX_HEADER_LEVEL = 6

HEADER_PATTERN = re.compile(
    '^' +
    '(?P<level_pre>={1,6})' +
        '(?P<title>.*?)' +
    '(?P<level_post>={1,6})\s*?' +
    '$'
)

HEADER_TAG = '='


class Header:

    def __init__(self, level, title):
        self.level = level
        self.title = title.strip()

    @classmethod
    def parse(cls, wikitext):
        # NOTE: This method is more restrictive than using regexp
        #       As it forces to use matching number of "=" on both sides
        wikitext = wikitext.strip()
        for level in range(MAX_HEADER_LEVEL, 0, -1):
            tag = HEADER_TAG*level
            if wikitext.startswith(tag) and wikitext.endswith(tag):
                break
        if not level:
            return

        title = wikitext[level: level*-1]
        return Header(level, title)

    def __repr__(self):
        return f'<{self.__class__.__name__} level={self.level}, title="{self.title}">'


class Section:

    def __init__(self, header=None):
        self.header = header
        self.sections = []
        # TODO: Consider renaming content to wikitext
        self.content = WikiText()

    @property
    def title(self):
        if self.header:
            return self.header.title

    @functools.cached_property
    def templates(self):
        return list(Template.find_all(self.content))

    @functools.cached_property
    def lists(self):
        return list(List.find_all(self.content))

    @functools.cached_property
    def tables(self):
        return list(Table.find_all(self.content))

    @classmethod
    def find_all(cls, wikitext):
        level = None
        sections = collections.deque()
        sections.append([Section(), ])
        content = []
        lines = WikitextIterator(wikitext, empty=True)
        for line in lines:
            if HEADER_PATTERN.match(line):
                header = Header.parse(line)
                if level and header.level > level:
                    sections.append([Section(), ])

                sections[-1][-1].content = WikiText('\n'.join(content))
                content.clear()

                while level and header.level < level:
                    subsections = sections.pop()
                    sections[-1][-1].sections = subsections
                    sections[-1][-1].content = WikiText('\n'.join(
                        section.content for section in subsections
                    ))
                    level -= 1

                level = header.level
                sections[-1].append(Section(header))

            content.append(line)

        sections[-1][-1].content = WikiText('\n'.join(content))
        while len(sections) > 1:
            subsections = sections.pop()
            sections[-1][-1].sections = subsections
            sections[-1][-1].content = WikiText('\n'.join(
                section.content for section in subsections
            ))

        return list(sections[0])

    def __repr__(self):
        if self.header:
            return f'<{self.__class__.__name__} title="{self.header.title}">'
        else:
            return f'<{self.__class__.__name__}>'


def tree(sections, level=0):
    for section in sections:
        print('   '*level, section)
        if section.sections:
            tree(section.sections, level+1)

