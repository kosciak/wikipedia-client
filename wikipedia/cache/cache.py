import logging
import os.path

from ..parser.core import is_page_id

from .db import PageDB, PageMetaDB


log = logging.getLogger('wikipedia.cache.cache')


class WikiCache:

    def __init__(self, *, meta_db='sqlite', page_db='fs', **kwargs):
        meta_db_cls = PageMetaDB.get_backend(meta_db)
        self.meta_db = meta_db_cls(**kwargs)
        page_db_cls = PageDB.get_backend(page_db)
        if page_db_cls == meta_db_cls:
            # Don't create second instance if same class implements both DB interfaces
            self.page_db = self.meta_db
        else:
            self.page_db = page_db_cls(**kwargs)

    def get_revision_id(self, lang, page_id):
        if not page_id:
            return
        return self.meta_db.get_revision_id(lang, page_id)

    def has_page(self, lang, page_id, title):
        page_id = page_id or self.get_page_id(lang, title)
        return self.get_revision_id(lang, page_id)

    def get_page_id(self, lang, title):
        if is_page_id(title):
            return title
        title = title.replace('_', ' ')
        return self.meta_db.get_page_id(lang, title)

    def get(self, lang, page_id, title):
        page_id = page_id or self.get_page_id(lang, title)
        return self.page_db.get_page(lang, page_id)

    def insert(self, page):
        self.page_db.insert_page(page)
        self.meta_db.insert_meta(page)

