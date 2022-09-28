import logging
import urllib.parse

import requests

from .parser.core import is_page_id, is_link
from .parser import WikiLink

from .cache import WikiCache

from .page import WikiPage


log = logging.getLogger('wikipedia.client')


# Query parameters templates

FORMAT_JSON = {
    'format': 'json', # specify data format
}

QUERY_RESOLVE_REDIRECTS = {
    'action': 'query',  # Fetch data from and about MediaWiki
                        # https://www.mediawiki.org/wiki/API:Query
    'redirects': '',    # Automatically resolve redirects
}

QUERY_PAGES_FULL = {
    'prop': '|'.join([  # https://www.mediawiki.org/wiki/API:Properties
        'info',         # Get basic page information
                        # https://www.mediawiki.org/wiki/API:Info
        'categoryinfo', # Returns information about the given categories
                        # https://www.mediawiki.org/wiki/API:Categoryinfo
        'pageprops',    # Get various page properties defined in the page content
                        # https://www.mediawiki.org/wiki/API:Pageprops
        'categories',   # List all categories the pages belong to
                        # https://www.mediawiki.org/wiki/API:Categories
        'extracts',     # Returns plain-text or limited HTML extracts of the given pages
                        # https://www.mediawiki.org/wiki/Extension:TextExtracts#API
        'revisions',    # Get revision information
                        # https://www.mediawiki.org/wiki/API:Revisions
        'coordinates',  # Returns coordinates of the given page
                        # https://www.mediawiki.org/wiki/Extension:GeoData#prop=coordinates
    ]),
    # prop = info
    'inprop': 'url',    # Gives a full URL, an edit URL, and the canonical URL for each page
    # prop = extracts
    'explaintext': '',  # Return extracts as plain text instead of limited HTML
    'exintro': '',      # Return only content before the first section
    # prop = revisions
    'rvprop': '|'.join([    # Which properties to get for each revision
        'ids',          # The ID of the revision
        'content',      # Content of each revision slot
    ]),
    # 'rvlimit': 1,       # Limit how many revisions will be returned
    #                     # NOTE: If specified continue with previous revid will be added
    'rvslots': '*',     # Which revision slots to return data for; '*' for all values
    # prop = categories
    'cllimit': 'max',   # How many categories to return
}

QUERY_PAGES_MINIMAL = {
    'prop': '|'.join([
        'info',
        'categoryinfo',
    ]),
    'inprop': 'url',
}

QUERY_LIST_CATEGORYMEMBERS = {
    'action': 'query',
    'list': 'categorymembers',  # List all pages in a given category
                                # Returns only limited info specified by cmprop
                                # https://www.mediawiki.org/wiki/API:Categorymembers
    'cmlimit': 'max',           # The maximum number of pages to return
    'cmprop': '|'.join([        # Which pieces of information to include
        'ids',                  # Adds the page ID
        'title',                # Adds the title and namespace ID of the page
    ]),
}

QUERY_GENERATOR_CATEGORYMEMBERS = {
    'generator': 'categorymembers',
    'gcmlimit': 'max',
}


# https://github.com/goldsmith/Wikipedia/blob/master/wikipedia/wikipedia.py
# https://github.com/5j9/wikitextparser


class Results:

    def __init__(self, api_url, params, response):
        self.api_url = api_url
        self.params = params
        self.response = response

    @property
    def request(self):
        return self.response.request

    @property
    def ok(self):
        return self.response.ok

    @property
    def status(self):
        return self.response.status_code

    @property
    def reason(self):
        return self.response.reason

    @property
    def data(self):
        return self.response.json()


class WikiClient:

    API_URL = 'https://%s.wikipedia.org/w/api.php'

    def __init__(self, lang, *, load=False, check_updates=False, **kwargs):
        self._lang = None
        self._api_url = None
        self.set_lang(lang)
        self._load_members = load
        self._check_updates = check_updates
        self._cache = WikiCache(**kwargs)
        self._session = requests.Session()

    @property
    def lang(self):
        return self._lang

    def set_lang(self, lang):
        self._lang = lang
        self._api_url = self.API_URL % (self._lang, )

    def _request(self, params, api_url=None):
        params.update(FORMAT_JSON)
        if not 'action' in params:
            # NOTE: By default use action=query module if not specified otherwise
            params['action'] = 'query'
        api_url = api_url or self._api_url
        response = self._session.get(
            api_url,
            params=params,
        )
        results = Results(
            api_url,
            params,
            response,
        )
        log.debug(
            'API: %s - %s',
            results.request.url, results.status,
        )
        return results

    def _continued(self, results):
        yield results
        while 'continue' in results.data:
            params = results.params
            params.update(results.data['continue'])
            results = self._request(
                params,
                results.api_url,
            )
            yield results

    def query_pages(self, **params):
        params.update(QUERY_RESOLVE_REDIRECTS)
        # NOTE: result = {'query': {'pages': {} }}
        return self._request(params)

    def query_page_ids(self, params, *page_ids):
        return self.query_pages(
            pageids='|'.join([
                str(page_id) for page_id in page_ids
            ]),
            **params,
        )

    def query_page_titles(self, params, *titles):
        return self.query_pages(
            titles='|'.join(titles),
            **params,
        )

    def query_list_category_members(self, category, cmtype=None):
        if is_page_id(category):
            query_for = 'cmpageid'      # Page ID of the category to enumerate
        else:
            query_for = 'cmtitle'       # Which category to enumerate, full title with prefix
        params = {
            query_for: category,
        }
        if cmtype:
            params['cmtype'] = cmtype   # Which type of category members to include: page|subcat|file
        params.update(QUERY_LIST_CATEGORYMEMBERS)
        # NOTE: result = {'query': {'categorymembers': [] }}
        return self._request(params)

    def query_category_members(self, category, cmtype=None):
        # Using generator instead of list, so we can query for additional pages' data pages
        # NOTE: Generator parameter names must be prefixed with a "g"
        if is_page_id(category):
            query_for = 'gcmpageid'
        else:
            query_for = 'gcmtitle'
        params = {
            query_for: category,
        }
        if cmtype:
            params['gcmtype'] = cmtype
        params.update(QUERY_RESOLVE_REDIRECTS)
        params.update(QUERY_GENERATOR_CATEGORYMEMBERS)
        params.update(QUERY_PAGES_MINIMAL)
        # NOTE: result = {'query': {'pages': {} }}
        return self._request(params)

    def query_category_pages(self, category):
        return self.query_category_members(category, 'page')

    def query_category_subcategories(self, category):
        return self.query_category_members(category, 'subcat')

    def _pages_gen(self, pages_data, load=False, check_updates=None):
        if load is None:
            load = self._load_members
        for data in pages_data:
            page = WikiPage(data)
            if load:
                page = self.page(page, check_updates=check_updates)
            yield page

    def _get_pages(self, results, load=None, check_updates=None):
        for results in self._continued(results):
            if not 'query' in results.data:
                # no members returned
                continue
            yield from self._pages_gen(
                results.data['query'].get('pages', {}).values(),
                load, check_updates,
            )

    def _get_categorymembers(self, results, load=None, check_updates=None):
        for results in self._continued(results):
            if not 'query' in results.data:
                # no members returned
                continue
            yield from self._pages_gen(
                results.data['query'].get('categorymembers', []),
                load, check_updates,
            )

    def category_members(self, category, load=None, check_updates=None):
        results = self.query_category_members(category.page_id or category.title)
        yield from self._get_pages(results, load, check_updates)

    def category_pages(self, category, load=None, check_updates=None):
        results = self.query_category_pages(category.page_id or category.title)
        yield from self._get_pages(results, load, check_updates)

    def category_subcategories(self, category, load=None, check_updates=None):
        results = self.query_category_subcategories(category.page_id or category.title)
        yield from self._get_pages(results, load, check_updates)

    def _get_page_id(self, page):
        if isinstance(page, WikiPage):
            return page.page_id
        if is_page_id(page):
            return page

    def _get_title(self, title):
        if isinstance(title, str):
            if title.startswith('https://'):
                # TODO: extract lang from URL and compare with current client's lang
                title = title[title.find('/wiki/')+6 :]
            elif is_link(title):
                # Follow a links title
                title = WikiLink.parse(title)
        if isinstance(title, WikiLink):
            title = title.title
        title = urllib.parse.unquote(title)
        return title

    def _get_revision_id(self, page):
        if isinstance(page, WikiPage):
            return page.revision_id

    def _page(self, page_id, title, params=None):
        params = params or QUERY_PAGES_FULL
        if page_id:
            results = self.query_page_ids(params, page_id)
        else:
            results = self.query_page_titles(params, title)
        for page in self._get_pages(results, load=False):
            return page

    def _cached_page(self, page_id, title, revision_id, check_updates=None):
        if check_updates is None:
            check_updates = self._check_updates

        cached_page = self._cache.get(
            self.lang, page_id, title,
        )
        if not cached_page:
            return

        if check_updates and not revision_id:
            # Get minimal data and check if revision_id changed
            page = self._page(page_id, title, QUERY_PAGES_MINIMAL)
            if page:
                revision_id = page.revision_id

        if revision_id and cached_page.revision_id < revision_id:
            # Cached page is older than given revision_id
            return

        return cached_page

    def page(self, page, check_updates=None):
        page_id = self._get_page_id(page)
        if not page_id:
            title = self._get_title(page)
        else:
            title = None

        if self._cache:
            revision_id = self._get_revision_id(page)
            cached_page = self._cached_page(
                page_id, title, revision_id, check_updates,
            )
            if cached_page:
                return cached_page

        page = self._page(page_id, title)
        if page and self._cache:
            self._cache.insert(page)

        return page

    def parse(self, page):
        # TODO: Do I need it? Might need some reworking
        # https://www.mediawiki.org/wiki/API:Parsing_wikitext
        # https://www.mediawiki.org/w/api.php?action=help&modules=parse
        if is_page_id(page):
            query_for = 'pageid'
        else:
            query_for = 'page'
        params = {
            'action': 'parse',
            query_for: page,
        }
        return self._request(params)

