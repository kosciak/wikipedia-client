import logging

from ..page import WikiPage


log = logging.getLogger('wikipedia.cache.db')


class DB:

    __BACKENDS = {}

    @classmethod
    def register(cls, name):
        def _register(backend_cls):
            cls.__BACKENDS[(cls.__name__, name)] = backend_cls
            return backend_cls
        return _register

    @classmethod
    def get_backend(cls, name):
        return cls.__BACKENDS.get((cls.__name__, name))


class PageDB(DB):

    def insert_page(self, page: WikiPage):
        raise NotImplementedError()

    def get_page(self, page_id: int) -> WikiPage:
        raise NotImplementedError()


class PageMetaDB(DB):

    def insert_page_meta(self, lang: str, page_id: int, title: str, revision_id: int):
        raise NotImplementedError()

    def insert_meta(self, page: WikiPage):
        return self.insert_page_meta(
            page.lang, page.page_id, page.title, page.revision_id,
        )

    def get_revision_id(self, lang: str, page_id: int) -> int:
        raise NotImplementedError()

    def get_page_id(self, lang: str, title: str) -> int:
        raise NotImplementedError()


def convert_meta_db_dbm_to_sqlite(dbm_db, sqlite_db):
    titles = {}
    revision_ids = {}

    db = dbm_db.get_ro_db()
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
        sqlite_db.insert_page_meta(lang, page_id, title, revision_id)

