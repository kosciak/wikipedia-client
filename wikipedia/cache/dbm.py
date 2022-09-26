import dbm
import logging
import os
import os.path

from .db import PageMetaDB


log = logging.getLogger('wikipedia.cache.dbm')


CACHE_FN = 'pages.db'


@PageMetaDB.register('dbm')
class DbmPageMetaDB(PageMetaDB):

    def __init__(self, *, cache_dir, fn=None, **kwargs):
        self.fn = os.path.join(cache_dir, fn or CACHE_FN)

    def get_ro_db(self):
        return dbm.open(self.fn, 'r')

    def insert_page_meta(self, lang, page_id, title, revision_id):
        with dbm.open(self.fn, 'c') as db:
            db[f'title:{lang}:{title}'] = str(page_id)
            db[f'revid:{lang}:{page_id}'] = str(revision_id)

    def get_revision_id(self, lang, page_id):
        with dbm.open(self.fn, 'c') as db:
            revision_id = db.get(f'revid:{lang}:{page_id}')
            if revision_id:
                return int(revision_id)

    def get_page_id(self, lang, title):
        with dbm.open(self.fn, 'c') as db:
            page_id = db.get(f'title:{lang}:{title}')
            if page_id:
                return page_id.decode()

