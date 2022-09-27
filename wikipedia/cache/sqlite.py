import logging
import sqlite3
import os
import os.path

import sql

from .db import PageMetaDB


log = logging.getLogger('wikipedia.cache.sqlite')


CACHE_FN = 'pages.sqlite'


PAGE_META = sql.Columns(
    'lang TEXT NOT NULL',
    'page_id INTEGER NOT NULL',
    'revision_id INTEGER NOT NULL',
    'title TEXT NOT NULL',
)

PAGE_META_TABLE = sql.Table(
    name='PageMeta',
    columns=PAGE_META,
).primary_key(
    PAGE_META.lang, PAGE_META.page_id, PAGE_META.revision_id,
)

INDEXES = [
    PAGE_META_TABLE.index('PageMeta_page_id_index', PAGE_META.lang, PAGE_META.page_id),
    PAGE_META_TABLE.index('PageMeta_title_index', PAGE_META.lang, PAGE_META.title),
]


Param = sql.QmarkParameter


@PageMetaDB.register('sqlite')
class SQLitePageMetaDB(PageMetaDB):

    def __init__(self, *, cache_dir, fn=None, **kwargs):
        self.fn = os.path.join(cache_dir, fn or CACHE_FN)
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            os.makedirs(
                os.path.dirname(self.fn),
                exist_ok=True,
            )
            self._connection = sqlite3.connect(self.fn)
            self._connection.row_factory = sqlite3.Row
            self._create_tables()
            self._create_indexes()
        return self._connection

    def execute_query(self, query, *params):
        return self.connection.execute(
            query.sql(),
            params,
        )

    def _create_tables(self):
        query = PAGE_META_TABLE.create(if_not_exists=True)
        self.execute_query(query)

    def _create_indexes(self):
        for index in INDEXES:
            query = index.create(if_not_exists=True)
            self.execute_query(query)

    def insert_page_meta(self, lang, page_id, revision_id, title):
        param = Param()
        query = PAGE_META_TABLE.insert({
            PAGE_META.lang: param('lang'),
            PAGE_META.page_id: param('page_id'),
            PAGE_META.title: param('title'),
            PAGE_META.revision_id: param('revision_id'),
        },
            replace=True,
        )
        self.execute_query(
            query,
            lang, page_id, title, revision_id,
        )
        self.connection.commit()

    def get_revision_id(self, lang, page_id):
        param = Param()
        query = PAGE_META_TABLE.select(
            PAGE_META.revision_id,
        ).where(
            PAGE_META.lang == param('lang'),
            PAGE_META.page_id == param('page_id'),
        ).order_by(
            PAGE_META.revision_id, order=sql.Order.DESC,
        )
        results = self.execute_query(
            query,
            lang, page_id,
        )
        for row in results:
            return row['revision_id']

    def get_page_id(self, lang, title):
        param = Param()
        query = PAGE_META_TABLE.select(
            PAGE_META.page_id,
        ).where(
            PAGE_META.lang == param('lang'),
            PAGE_META.title == param('title'),
        )
        results = self.execute_query(
            query,
            lang, title,
        )
        for row in results:
            return row['page_id']

    def all_page_meta(self):
        query = PAGE_META_TABLE.select(
            PAGE_META.lang, PAGE_META.page_id, PAGE_META.title, PAGE_META.revision_id,
        )
        results = self.execute_query(query)
        for row in results:
            yield (
                row['lang'], row['page_id'], row['revision_id'], row['title'],
            )

