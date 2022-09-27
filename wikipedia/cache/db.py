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

    def insert_page_meta(self, lang: str, page_id: int, revision_id: int, title: str):
        raise NotImplementedError()

    def insert_meta(self, page: WikiPage):
        return self.insert_page_meta(
            page.lang, page.page_id,  page.revision_id,page.title,
        )

    def get_revision_id(self, lang: str, page_id: int) -> int:
        raise NotImplementedError()

    def get_page_id(self, lang: str, title: str) -> int:
        raise NotImplementedError()

    def all_page_meta(self):
        # yield (lang, page_id, revision_id, title)
        raise NotImplementedError()


def copy_page_meta_db(source_db, destination_db):
    for lang, page_id, revision_id, title in source_db.all_page_meta():
        destination_db.insert_page_meta(
            lang, page_id, revision_id, title,
        )

