import collections
import logging

from .core import WikitextIterator


log = logging.getLogger('wikipedia.parser.tables')


# https://en.wikipedia.org/wiki/Help:Table

TABLE_START = '{|'
TABLE_CAPTION = '|+'
TABLE_ROW = '|-'
TABLE_HEADER = '!'
TABLE_CELL = '|'
TABLE_END = '|}'

HEADER_CELLS_SEPARATOR = '!!'
ROW_CELLS_SEPARATOR = '||'


class Table:

    def __init__(self):
        self.caption = None
        self.header = []
        self.rows = []

    def __iter__(self):
        yield from self.rows

    @classmethod
    def parse_cells(cls, wikitext, separator):
        # TODO: remove params like class="..." style=".." | <content>
        return wikitext.split(separator)

    @classmethod
    def find_all(cls, wikitext):
        table = None
        row = []
        lines = WikitextIterator(wikitext)
        for line in lines:
            if line.startswith(TABLE_START):
                table = Table()
                row = []
            if table:
                if line.startswith(TABLE_END):
                    if row:
                        table.rows.append(row)
                        row = []
                    yield table
                elif line.startswith(TABLE_CAPTION):
                    table.caption = line[2:].strip()
                elif line.startswith(TABLE_ROW):
                    if row:
                        table.rows.append(row)
                        row = []
                elif line.startswith(TABLE_HEADER):
                    cells = line[1:].lstrip(' ')
                    # TODO: https://en.wikipedia.org/wiki/Help:Table#Row_headers
                    table.header.extend(
                        cls.parse_cells(cells, HEADER_CELLS_SEPARATOR)
                    )
                elif line.startswith(TABLE_CELL):
                    cells = line[1:].lstrip(' ')
                    row.extend(
                        cls.parse_cells(cells, ROW_CELLS_SEPARATOR)
                    )

    def __repr__(self):
        if self.caption:
            return f'<{self.__class__.__name__} caption="{self.caption}">'
        else:
            return f'<{self.__class__.__name__}>'

