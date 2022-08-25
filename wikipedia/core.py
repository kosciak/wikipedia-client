import logging

import dateutil.parser

from ..geojson import Coordinates


log = logging.getLogger('wikipedia.core')


def is_page_id(page_id):
    if isinstance(page_id, int):
        return True
    if (isinstance(page_id, str) and page_id.isnumeric()):
        return True
    return False


def parse_infobox_data(content):
    data = {}
    is_infobox = False
    for line in content.splitlines():
        if not line:
            continue
        if is_infobox and line == '}}':
            return data
        if not is_infobox and line.startswith('{{'):
            is_infobox = True
            continue
        if is_infobox and line.startswith(' |'):
            line = line.lstrip('| ')
            key, sep, value = line.partition(' = ')
            value = value.strip()
            if value:
                data[key.strip()] = value.strip()


def parse_link_title(link):
    target, sep, title = link.strip('[]').partition('|')
    return title or target

def parse_link_target(link):
    target, sep, title = link.strip('[]').partition('|')
    return target


class WikiPage:

    def __init__(self, data):
        self._data = data

    def load(self, client, cache=False):
        page = client.page(self.page_id, cache=cache)
        self.update(page)

    def update(self, other):
        self._data.update(other._data)

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
    def categories(self):
        return [WikiPage(category) for category in self._data.get('categories', [])]

    @property
    def extract(self):
        return self._data.get('extract')

    @property
    def content(self):
        if 'revisions' in self._data:
            return self._data['revisions'][0]['slots']['main']['*']

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

