import collections
import logging
import re

from .wikitext import WikiText, WikitextIterator


log = logging.getLogger('wikipedia.parser.tables')


# https://en.wikipedia.org/wiki/Help:Table
# https://www.mediawiki.org/wiki/Help:Tables

TABLE_START_PATTERN = re.compile(
    '^ *' +
    '{\|' + # {|
    ' *' +
    '(?P<attributes>.*?)' + # attributes
    ' *$'
)

TABLE_CAPTION_PATTERN = re.compile(
    '^ *' +
    '\|\+' + # |+
    ' *' +
    '(?P<content>.*?)' + # attributes
    ' *$'
)

TABLE_ROW_PATTERN = re.compile(
    '^ *' +
    '\|-' + # |-
    ' *' +
    '(?P<attributes>.*?)' + # attributes
    ' *$'
)

TABLE_CELL_PATTERN = re.compile(
    '^ *' +
    '[!|]' +
    '(?![-+}])' # NOT followed by +, -, }
)

TABLE_END_PATTERN = re.compile(
    '^ *' +
    '\|}'
)

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

ATTRIBUTE_PATTERN = re.compile(
    ' *' +
    '(?P<key>[^ =]+?)' + # key: string without " " or "="
    '=' +
    '(["])?' + # might be quoted
    '(?P<value>(?(2)[^"]+?|[^ ]+?))' + # value: if quoted until next quote, otherwise until " "
    '(?(2)")' + # if quoted end with quote
    '(?= |$)'
)

TABLE_HEADER = '!'
TABLE_CELL = '|'
ATTRIBUTES_SEPARATOR = '|'
HEADER_CELLS_SEPARATOR = '!!'
ROW_CELLS_SEPARATOR = '||'


def parse_attributes(attributes):
    if not attributes:
        return {}
    attrs = {
        match['key']: match['value']
        for match in ATTRIBUTE_PATTERN.finditer(attributes)
    }
    return attrs


class Cell(WikiText):

    def __new__(cls, s, *, attributes=None):
        s = super().__new__(cls, s)
        s.attributes = attributes or {}
        return s

    @classmethod
    def find_all(cls, wikitext):
        for match in CELL_PATTERN.finditer(wikitext):
            cell_cls = CELL_CLS[match['type']]
            yield cell_cls(
                match['content'],
                attributes=parse_attributes(match['attributes']),
            )


class Header(Cell):
    pass


class Row(list):

    def __init__(self, iterable=None, /, *, attributes=None):
        self.attributes = attributes or {}
        super().__init__(iterable or [])

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


CELL_CLS = {
    '!': Header,
    '|': Cell,
    '!!': Header,
    '||': Cell,
}


class Table:

    def __init__(self, *, attributes=None, caption=None, rows=None):
        self.attributes = attributes
        self.caption = caption
        self.rows = rows or []

    def __iter__(self):
        yield from self.rows

    @classmethod
    def find_all(cls, wikitext):
        table = None
        row = None
        lines = WikitextIterator(wikitext, empty=False)
        for line in lines:
            match = TABLE_START_PATTERN.match(line)
            if match:
                # TODO: This is going to fail with nested tables!
                table = Table(
                    attributes=parse_attributes(match['attributes']),
                )
                row = Row()
            if table:
                if TABLE_END_PATTERN.match(line):
                    # TODO: This is going to fail with nested tables!
                    if row:
                        table.rows.append(row)
                    yield table
                    table = None
                    continue

                if TABLE_CELL_PATTERN.match(line):
                    # TODO: This will work ONLY with single line cells
                    #       Need support for multiline cell contents
                    row.extend(
                        Cell.find_all(line)
                    )
                    continue

                match = TABLE_CAPTION_PATTERN.match(line)
                if match:
                    table.caption = WikiText(match['content'])
                    continue

                match = TABLE_ROW_PATTERN.match(line)
                if match:
                    if row:
                        table.rows.append(row)
                    row = Row(
                        attributes=parse_attributes(match['attributes']),
                    )

    def __repr__(self):
        if self.caption:
            return f'<{self.__class__.__name__} caption="{self.caption}">'
        else:
            return f'<{self.__class__.__name__}>'

