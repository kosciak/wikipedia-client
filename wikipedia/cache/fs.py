import logging
import os
import os.path
import json

from ..page import WikiPage

from .db import PageDB


log = logging.getLogger('wikipedia.cache.fs')


@PageDB.register('fs')
class FilePageDB(PageDB):

    def __init__(self, *, cache_dir, **kwargs):
        self.cache_dir = cache_dir

    def get_page_fn(self, lang, page_id):
        page_fn = os.path.join(
            self.cache_dir,
            f'{lang}_{page_id}.json',
        )
        return page_fn

    def insert_page(self, page):
        if not page.page_id:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        page_fn = self.get_page_fn(page.lang, page.page_id)
        with open(page_fn, 'w') as f:
            json.dump(page._data, f, indent=2)

    def get_page(self, lang, page_id):
        if not page_id:
            return
        page_fn = self.get_page_fn(lang, page_id)
        if os.path.exists(page_fn):
            with open(page_fn, 'r') as f:
                return WikiPage(json.load(f))

