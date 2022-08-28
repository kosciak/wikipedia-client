import dbm
import logging
import os
import os.path
import json

from .core import WikiPage
from .core import is_page_id


log = logging.getLogger('wikipedia.cache')


WIKI_CACHE_DIR = os.path.join(
    'data',
    'wiki_cache',
)


class WikiCache:

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or WIKI_CACHE_DIR
        self._db_fn = os.path.join(self.cache_dir, 'pages.db')

    def get_page_fn(self, lang, page_id):
        page_fn = os.path.join(
            self.cache_dir,
            f'{lang}_{page_id}.json',
        )
        return page_fn

    def get_revision_id(self, lang, page_id):
        if not page_id:
            return
        with dbm.open(self._db_fn, 'c') as db:
            revision_id = db.get(f'revid:{lang}:{page_id}')
            if revision_id:
                return int(revision_id)

    def has_page(self, lang, page_id, title):
        page_id = page_id or self.get_page_id(lang, title)
        return self.get_revision_id(lang, page_id)

    def get_page_id(self, lang, page):
        if is_page_id(page):
            return page
        page = page.replace('_', ' ')
        with dbm.open(self._db_fn, 'c') as db:
            page_id = db.get(f'title:{lang}:{page}')
            if page_id:
                return page_id.decode()

    def get(self, lang, page_id, title):
        page_id = page_id or self.get_page_id(lang, title)
        if not page_id:
            return
        page_fn = self.get_page_fn(lang, page_id)
        if os.path.exists(page_fn):
            with open(page_fn, 'r') as f:
                return WikiPage(json.load(f))

    def insert(self, page):
        if not page.page_id:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        page_fn = self.get_page_fn(page.lang, page.page_id)
        with open(page_fn, 'w') as f:
            json.dump(page._data, f, indent=2)
        with dbm.open(self._db_fn, 'c') as db:
            db[f'title:{page.lang}:{page.title}'] = str(page.page_id)
            db[f'revid:{page.lang}:{page.page_id}'] = str(page.revision_id)

