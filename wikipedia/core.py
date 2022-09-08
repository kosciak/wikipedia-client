import logging

from .links import WikiLink


log = logging.getLogger('wikipedia.core')


NESTED_TAGS_START = {
    '[[',
    '{{',
}

NESTED_TAGS_END = {
    ']]',
    '}}',
}


def is_page_id(page_id):
    if isinstance(page_id, int):
        return True
    if (isinstance(page_id, str) and page_id.isnumeric()):
        return True
    return False


def is_link(link):
    if not link:
        return False
    return link.startswith('[[') and link.endswith(']]') and link.rfind('[[') == 0


def parse_text(wikitext):
    if is_link(wikitext):
        return WikiLink.parse(wikitext).text
    else:
        return wikitext

