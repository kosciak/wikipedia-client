import dbm
import sqlite3
import logging
import os
import os.path
import json

from .core import is_page_id
from .page import WikiPage


log = logging.getLogger('wikipedia.cache')


WIKI_CACHE_DIR = os.path.join(
    'data',
    'wiki_cache',
)


class DbmDB:

    def __init__(self, fn):
        self.fn = fn

    def get_ro_db(self):
        return dbm.open(self.fn, 'r')

    def insert_page_meta(self, lang, page_id, title, revision_id):
        with dbm.open(self.fn, 'c') as db:
            db[f'title:{page.lang}:{page.title}'] = str(page.page_id)
            db[f'revid:{page.lang}:{page.page_id}'] = str(page.revision_id)

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


class SQLiteDB:

    def __init__(self, fn):
        self.fn = fn
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self.fn)
            self._create_tables()
        return self._connection

    def _create_tables(self):
        self.connection.execute('''
            CREATE TABLE IF NOT EXISTS page_meta (
                lang TEXT NOT NULL,
                page_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                revision_id INTEGER NOT NULL,
                PRIMARY KEY (lang, page_id)
            );
        ''')

    def insert_page_meta(self, lang, page_id, title, revision_id):
        self.connection.execute(
            'INSERT OR REPLACE INTO page_meta VALUES (?, ?, ?, ?)',
            (lang, page_id, title, revision_id),
        )
        self.connection.commit()

    def get_revision_id(self, lang, page_id):
        result = self.connection.execute(
            'SELECT revision_id FROM page_meta WHERE lang=? AND page_id=?',
            (lang, page_id),
        )
        for row in result.fetchall():
            return row[0]

    def get_page_id(self, lang, title):
        result = self.connection.execute(
            'SELECT page_id FROM page_meta WHERE lang=? AND title=?',
            (lang, title),
        )
        for row in result.fetchall():
            return row[0]


def dbm_to_sqlite(dbm_db, sqlite_db):
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


class WikiCache:

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or WIKI_CACHE_DIR
        # self.db = DbmDB(
        #     os.path.join(self.cache_dir, 'pages.db')
        # )
        self.db = SQLiteDB(
            os.path.join(self.cache_dir, 'pages.sqlite')
        )

    def get_page_fn(self, lang, page_id):
        page_fn = os.path.join(
            self.cache_dir,
            f'{lang}_{page_id}.json',
        )
        return page_fn

    def get_revision_id(self, lang, page_id):
        if not page_id:
            return
        return self.db.get_revision_id(lang, page_id)

    def has_page(self, lang, page_id, title):
        page_id = page_id or self.get_page_id(lang, title)
        return self.get_revision_id(lang, page_id)

    def get_page_id(self, lang, page):
        if is_page_id(page):
            return page
        page = page.replace('_', ' ')
        return self.db.get_page_id(lang, page)

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
        self.db.insert_page_meta(
            page.lang, page.page_id, page.title, page.revision_id,
        )

