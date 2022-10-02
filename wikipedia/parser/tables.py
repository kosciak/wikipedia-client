import collections
import logging
import re

from .wikitext import WikiText, WikitextIterator


log = logging.getLogger('wikipedia.parser.tables')


# https://en.wikipedia.org/wiki/Help:Table
# https://www.mediawiki.org/wiki/Help:Tables

TABLE_START_PATTERN = re.compile('^ *{\|')
TABLE_CAPTION_PATTERN = re.compile('^ *\|\+')
TABLE_ROW_PATTERN = re.compile('^ *\|-')
TABLE_CELL_PATTERN = re.compile('^ *[!|]')
TABLE_END_PATTERN = re.compile('^ *\|}')

CELL_PATTERN = re.compile(
    '(?P<type>^[!|]|[!|]{2})' + # Single pipe on beginning of line or two pipes if continuation
    '(?:' +
        ' *' +
        '(?P<attributes>[^|]*?)' + # attributes
        ' *' +
        '\|(?!\|)' + # Followed by single pipe
    ')?' +
    '\s*(?P<content>.*?)\s*?' +
    '(?=[!|]{2}|$)' # Contents until || or !!
)

TABLE_HEADER = '!'
TABLE_CELL = '|'
ATTRIBUTES_SEPARATOR = '|'
HEADER_CELLS_SEPARATOR = '!!'
ROW_CELLS_SEPARATOR = '||'


class Cell(WikiText):

    def __new__(cls, s, attributes=None):
        s = super().__new__(cls, s)
        s.attributes = attributes
        return s

    @classmethod
    def find_all(cls, wikitext):
        for match in CELL_PATTERN.finditer(wikitext):
            if TABLE_HEADER in match['type']:
                cell_cls = Header
            else:
                cell_cls = Cell
            yield cell_cls(
                match['content'],
                match['attributes'],
            )


class Header(Cell):
    pass


class Row(list):

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


class Table:

    def __init__(self):
        self.caption = None
        self.rows = []

    def __iter__(self):
        yield from self.rows

    @classmethod
    def find_all(cls, wikitext):
        table = None
        cells = []
        lines = WikitextIterator(wikitext, strip=True, empty=False)
        for line in lines:
            if TABLE_START_PATTERN.match(line):
                # TODO: This is going to fail with nested tables!
                table = Table()
                cells.clear()
            if table:
                if TABLE_END_PATTERN.match(line):
                    if cells:
                        table.rows.append(Row(cells))
                        cells.clear()
                    yield table
                elif TABLE_CAPTION_PATTERN.match(line):
                    table.caption = line[2:].strip()
                elif TABLE_ROW_PATTERN.match(line):
                    if cells:
                        table.rows.append(Row(cells))
                        cells.clear()
                elif TABLE_CELL_PATTERN.match(line):
                    cells.extend(
                        Cell.find_all(line)
                    )

    def __repr__(self):
        if self.caption:
            return f'<{self.__class__.__name__} caption="{self.caption}">'
        else:
            return f'<{self.__class__.__name__}>'

