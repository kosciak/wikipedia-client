import logging

import dateutil.parser

from .template import Template
from .table import Table


log = logging.getLogger('wikipedia.page')


class WikiPage:

    def __init__(self, data):
        self._data = data
        self._cache = {}

    def _clear_cached(self):
        self._cache.clear()

    def load(self, client, cache=False):
        page = client.page(self.page_id, cache=cache)
        self.update(page)

    def update(self, other):
        self._data.update(other._data)
        self._clear_cached()

    @property
    def is_missing(self):
        return 'missing' in self._data

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
        if self.has_content and not 'templates' in self._cache:
            self._cache['templates'] = list(Template.find_all(self.content))
        return self._cache.get('templates', [])

    @property
    def infobox(self):
        if self.has_content and not 'infobox' in self._cache:
            templates = self.templates or []
            for template in templates:
                if 'infobox' in template.name.lower():
                    self._cache['infobox'] = template
                    break
        return self._cache.get('infobox')

    @property
    def tables(self):
        if self.has_content and not 'tables' in self._cache:
            self._cache['tables'] = list(Table.find_all(self.content))
        return self._cache.get('tables', [])

    @property
    def coordinates(self):
        if not 'coordinates' in self._data:
            return
        return dict(
            lat=self._data['coordinates'][0]['lat'],
            lon=self._data['coordinates'][0]['lon'],
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

