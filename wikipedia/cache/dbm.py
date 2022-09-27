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

    def insert_page_meta(self, lang, page_id, revision_id, title):
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

    def all_page_meta(self):
        titles = {}
        revision_ids = {}

        with dbm.open(self.fn, 'c') as db:
            for key in db.keys():
                if key.startswith(b'title'):
                    _, lang, title = key.split(b':', 2)
                    page_id = int(db.get(key))
                    titles[(lang.decode(), page_id)] = title.decode()
                elif key.startswith(b'revid'):
                    _, lang, page_id = key.split(b':')
                    revision_id = int(db.get(key))
                    revision_ids[(lang.decode(), int(page_id))] = revision_id

        for (lang, page_id), title in titles.items():
            revision_id = revision_ids.get((lang, page_id))
            yield (
                lang, page_id, revision_id, title,
            )

