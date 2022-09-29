import collections
import logging

from .core import WikitextIterator


log = logging.getLogger('wikipedia.parser.tables')


# https://en.wikipedia.org/wiki/Help:Section

MAX_HEADER_LEVEL = 6

HEADER_START = '='
HEADER_END = '='


class Header:

    def __init__(self, level, title):
        self.level = level
        self.title = title.strip()

    @classmethod
    def parse(cls, wikitext):
        wikitext = wikitext.strip()
        for level in range(MAX_HEADER_LEVEL, 0, -1):
            tag = HEADER_START*level
            if wikitext.startswith(tag) and wikitext.endswith(tag):
                break
        if not level:
            return

        title = wikitext.strip(HEADER_START)
        return Header(level, title)

    def __repr__(self):
        return f'<{self.__class__.__name__} level={self.level}, title="{self.title}">'


class Section:

    def __init__(self, header=None):
        self.header = header
        self.sections = []
        # TODO: Consider renaming content to wikitext
        self.content = ''

    @classmethod
    def find_all(cls, wikitext):
        level = None
        sections = collections.deque()
        sections.append([Section(), ])
        content = []
        lines = WikitextIterator(wikitext, strip=False, empty=True)
        for line in lines:
            if line.startswith(HEADER_START) and line.endswith(HEADER_END):
                header = Header.parse(line)
                if level and header.level > level:
                    sections.append([Section(), ])

                sections[-1][-1].content = '\n'.join(content)
                content.clear()

                while level and header.level < level:
                    subsections = sections.pop()
                    sections[-1][-1].sections = subsections
                    sections[-1][-1].content = '\n'.join(
                        section.content for section in subsections
                    )
                    level -= 1

                level = header.level
                sections[-1].append(Section(header))

            content.append(line)

        sections[-1][-1].content = '\n'.join(content)
        while len(sections) > 1:
            subsections = sections.pop()
            sections[-1][-1].sections = subsections
            sections[-1][-1].content = '\n'.join(
                section.content for section in subsections
            )

        return list(sections[0])


def tree(sections, level=0):
    for section in sections:
        print('   '*level, section.header)
        if section.sections:
            tree(section.sections, level+1)

