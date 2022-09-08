import collections
import logging


log = logging.getLogger('wikipedia.table')


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
    def find_all(cls, content):
        # NOTE: Using deque() so we can push back part of line and parse as new line
        lines = collections.deque(
            line.strip() for line
            in content.splitlines()
            if line.strip()
        )
        lines.reverse()
        table = None
        row = []
        while lines:
            line = lines.pop()
            if line.startswith('{|'):
                table = Table()
            if table:
                if line.startswith('|}'):
                    yield table
                elif line.startswith('|+'):
                    table.caption = line[2:].strip()
                elif line.startswith('|-'):
                    if row:
                        table.rows.append(row)
                        row = []
                elif line.startswith('!'):
                    cells = line.lstrip('! ')
                    table.header.extend(cls.parse_cells(cells, '!!'))
                elif line.startswith('|'):
                    cells = line.lstrip('| ')
                    row.extend(cls.parse_cells(cells, '||'))

    def __repr__(self):
        if self.caption:
            return f'<{self.__class__.__name__} caption="{self.caption}">'
        else:
            return f'<{self.__class__.__name__}>'

