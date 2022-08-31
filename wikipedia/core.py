import collections
import logging
import re

import dateutil.parser

from ..geojson import Coordinates


log = logging.getLogger('wikipedia.core')


WIKI_LINK_PATTERN = re.compile(
    '\[\[' +
        '(?P<title>[^#|\]]+)?' +
        '(?:#(?P<anchor>[^|\]]+))?' +
        '(?:\|(?P<label>[^\]]+))?' +
    '\]\]'
)

NESTED_TAGS_START = {
    '[[',
    '{{',
}

NESTED_TAGS_END = {
    ']]',
    '}}',
}


def is_page_id(page_id):
    if isinstance(page_id, int):
        return True
    if (isinstance(page_id, str) and page_id.isnumeric()):
        return True
    return False


def is_link(link):
    if not link:
        return False
    return link.startswith('[[') and link.endswith(']]') and link.rfind('[[') == 0


def parse_text(wikitext):
    if is_link(wikitext):
        return WikiLink.parse(wikitext).text
    else:
        return wikitext


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
    def parse(cls, link):
        if not is_link(link):
            return
        match = WIKI_LINK_PATTERN.match(link)
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


class Template:

    def __init__(self, name):
        self.name = name
        self.named_params = {}
        self.numbered_params = []

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.named_params.get(
                str(key),
                self.numbered_params[key-1],
            )
        if isinstance(key, slice):
            raise TypeError('Slice not supported!')
        else:
            return self.named_params[key]

    def get(self, key):
        return self.named_params.get(key)

    def __contains__(self, key):
        return key in self.named_params

    def keys(self):
        return self.named_params.keys()

    @classmethod
    def split_params(cls, wikitext):
        start = 0
        nested_level = 0
        for i in range(len(wikitext)):
            sequence = wikitext[i:i+2]
            if sequence in NESTED_TAGS_START:
                nested_level += 1
            elif sequence in NESTED_TAGS_END:
                nested_level -= 1
            if wikitext[i] == '|' and not nested_level:
                yield wikitext[start:i]
                start = i+1
        yield wikitext[start:]

    def parse_params(self, params):
        for param in self.split_params(params):
            name, is_named, value = param.partition('=')
            name = name.strip()
            if is_named:
                value = value.strip()
                if value:
                    self.named_params[name] = value
            else:
                self.numbered_params.append(name)

    @classmethod
    def find_all(cls, content):
        # NOTE: Using deque() so we can push back part of line and parse as new line
        lines = collections.deque(
            line.strip() for line
            in content.splitlines()
            if line.strip()
        )
        lines.reverse()
        template = None
        while lines:
            line = lines.pop()
            if line.startswith('{{'):
                # NOTE: Fix {{template|...}}{{another_template
                end = line.find('}}')
                start = line.find('{{', 1)
                if start > end:
                    lines.append(line[start:])
                    line = line[:start]

                name = line.strip('{}')
                name, has_params, params = name.partition('|')
                template = Template(name)
                if has_params:
                    template.parse_params(params)
            if template:
                if line.startswith('|'):
                    template.parse_params(line[1:])
                elif line.startswith('}}') or line.endswith('}}'):
                    yield template
                    template = None

    def __repr__(self):
        return f'<{self.__class__.__name__} name="{self.name}">'


class WikiPage:

    def __init__(self, data):
        self._data = data
        self._templates = None
        self._infobox = None

    def _clear_cached(self):
        self._templates = None
        self._infobox = None

    def load(self, client, cache=False):
        page = client.page(self.page_id, cache=cache)
        self.update(page)

    def update(self, other):
        self._data.update(other._data)
        self._clear_cached()

    @property
    def page_id(self):
        return self._data.get('pageid')

    @property
    def title(self):
        return self._data.get('title')

    @property
    def namespace_id(self):
        # Reference: https://en.wikipedia.org/wiki/Wikipedia:Namespace#Programming
        return self._data.get('ns')

    @property
    def namespace(self):
        if ':' in self.title:
            return self.title[:self.title.find(':')]

    @property
    def is_category(self):
        return self.namespace_id == 14

    @property
    def lang(self):
        return self._data.get('pagelanguage')

    @property
    def changed(self):
        if 'touched' in self._data:
            return dateutil.parser.isoparse(self._data['touched'])

    @property
    def revision_id(self):
        return self._data.get('lastrevid')

    @property
    def url(self):
        return self._data.get('fullurl')

    @property
    def is_disambiguation(self):
        if 'pageprops' in self._data:
            return 'disambiguation' in self._data['pageprops']

    @property
    def categories(self):
        return [WikiPage(category) for category in self._data.get('categories', [])]

    @property
    def extract(self):
        return self._data.get('extract')

    @property
    def has_content(self):
        return 'revisions' in self._data

    @property
    def content(self):
        if 'revisions' in self._data:
            return self._data['revisions'][0]['slots']['main']['*']

    @property
    def templates(self):
        if self._templates is None and self.has_content:
            self._templates = list(Template.find_all(self.content))
        return self._templates

    @property
    def infobox(self):
        if self._infobox is None and self.has_content:
            templates = self.templates or []
            for template in templates:
                if 'infobox' in template.name.lower():
                    self._infobox = template
                    break
        return self._infobox

    @property
    def coordinates(self):
        if not 'coordinates' in self._data:
            return
        return Coordinates(
            self._data['coordinates'][0]['lat'],
            self._data['coordinates'][0]['lon'],
        )

    @property
    def pages_num(self):
        if 'categoryinfo' in self._data:
            return self._data['categoryinfo']['pages']

    @property
    def subcategories_num(self):
        if 'categoryinfo' in self._data:
            return self._data['categoryinfo']['subcats']

    def __repr__(self):
        if 'pageid' in self._data:
            return f'<{self.__class__.__name__} page_id={self.page_id}, title="{self.title}">'
        return f'<{self.__class__.__name__} title="{self.title}">'

