import collections
import logging

from .links import WikiLink


log = logging.getLogger('wikipedia.parser.core')



def is_page_id(page_id):
    if isinstance(page_id, int):
        return True
    if (isinstance(page_id, str) and page_id.isnumeric()):
        return True
    return False


def is_link(wikitext):
    if not wikitext:
        return False
    return wikitext.startswith('[[') and wikitext.endswith(']]') and wikitext.rfind('[[') == 0


def is_template(wikitext):
    if not wikitext:
        return False
    return wikitext.startswith('{{') and wikitext.endswith('}}') and wikitext.rfind('{{') == 0


def get_text(wikitext):
    if not wikitext:
        return
    wikitext = wikitext.strip()
    if is_link(wikitext):
        return WikiLink.parse(wikitext).text
    if is_template(wikitext):
        wikitext = wikitext.strip('{}')
        name, sep, text = wikitext.partition('|')
        return text
    else:
        return wikitext


class WikitextIterator:

    def __init__(self, wikitext, strip=True, empty=True):
        # NOTE: Using deque() so we can push back part of line and parse as new line
        self.strip = strip
        self.empty = empty
        self.lines = collections.deque(
            wikitext.splitlines()
        )
        self.lines.reverse()

    def push(self, *lines):
        for line in reversed(lines):
            self.lines.append(line)

    def __iter__(self):
        while self.lines:
            line = self.lines.pop()
            if self.strip:
                line = line.strip()
            if (not self.empty) and (not line):
                continue
            yield line

