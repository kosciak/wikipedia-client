import dbm
import logging
import os
import os.path
import json

from .core import is_page_id


log = logging.getLogger('wikipedia.cache')


WIKI_CACHE_DIR = os.path.join(
    'data',
    'wiki_cache',
)


class WikiCache:

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or WIKI_CACHE_DIR
        self._db_fn = os.path.join(self.cache_dir, 'page_ids.db')

    def get_page_id(self, page):
        if is_page_id(page):
            return page
        page = page.replace('_', ' ')
        fn = os.path.join(self.cache_dir, 'page_ids.db')
        with dbm.open(self._db_fn, 'c') as db:
            page_id = db.get(page)
            if page_id:
                return page_id.decode()

    def get(self, page_id):
        page_id = self.get_page_id(page_id)
        if not page_id:
            return
        fn = os.path.join(self.cache_dir, f'{page_id}.json')
        if os.path.exists(fn):
            with open(fn, 'r') as f:
                return WikiPage(json.load(f))

    def insert(self, page):
        if not page.page_id:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        fn = os.path.join(self.cache_dir, f'{page.page_id}.json')
        with open(fn, 'w') as f:
            json.dump(page._data, f, indent=2)
        with dbm.open(self._db_fn, 'c') as db:
            # TODO: Store lang! <lang>:<title>
            db[page.title] = str(page.page_id)
            # TODO: Store revision_id of page_id

