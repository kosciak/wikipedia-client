import collections
import logging
import re

from .wikitext import WikiText, WikitextIterator


log = logging.getLogger('wikipedia.parser.lists')


# https://en.wikipedia.org/wiki/Help:List
# https://meta.wikimedia.org/wiki/Help:List


# NOTE: This will return ALL lists, includiing lists inside table cells!
# TODO: Does it need fixing?


ITEM_PATTERN = re.compile(
    '^' +
    '(?P<lists>' +
        '(?P<parents>[#*:;]*)' +
        '(?P<type>[#*:;])' +
    ') *' +
    '(?P<content>.*)' +
    '\s*$'
)

ORDERED_TAG = '#'
UNORDERED_TAG = '*'
TERM_TAG = ';'
DEFINITION_TAG = ':'


class List(list):

    @classmethod
    def sublist_or_yield(cls, lists):
        l = lists.pop()
        if lists:
            lists[-1].append(l)
        elif isinstance(l, cls):
            # NOTE: Only yield list instances of current class,
            #       so you can use List.find_all() returing all lists
            #       or OrderedList.find_all() to return only ordered ones
            yield l

    @classmethod
    def find_all(cls, wikitext):
        lists = collections.deque()
        lines = WikitextIterator(wikitext, empty=True)
        for line in lines:
            match = ITEM_PATTERN.match(line)
            if not match:
                while lists:
                    yield from cls.sublist_or_yield(lists)
                continue

            declared_lists_cls = [
                LIST_CLS[list_type] for list_type in match['lists']
            ]
            for i, list_cls in enumerate(declared_lists_cls):
                if len(lists) > i and not isinstance(lists[i], list_cls):
                    while len(lists) > i:
                        yield from cls.sublist_or_yield(lists)
                if len(lists) < i+1:
                    lists.append(list_cls())
            while len(lists) > len(declared_lists_cls):
                yield from cls.sublist_or_yield(lists)

            content = match['content']
            item = ITEM_CLS[match['type']](content)
            if isinstance(item, Term):
                # NOTE: Support for single line DescriptionList "; term : definition"
                definition_start = content.find(DEFINITION_TAG)
                if definition_start > 0:
                    item.content = content[:definition_start].strip()
                    lines.push(content[definition_start:])

            print(repr(item))
            lists[-1].append(item)

        while lists:
            yield from cls.sublist_or_yield(lists)

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


class OrderedList(List):
    pass

class UnorderedList(List):
    pass

class DescriptionList(List):
    pass


class ListItem(WikiText):
    pass

class Term(ListItem):
    pass

class Definition(ListItem):
    pass


LIST_CLS = {
    ORDERED_TAG: OrderedList,
    UNORDERED_TAG: UnorderedList,
    TERM_TAG: DescriptionList,
    DEFINITION_TAG: DescriptionList,
}

ITEM_CLS = {
    ORDERED_TAG: ListItem,
    UNORDERED_TAG: ListItem,
    TERM_TAG: Term,
    DEFINITION_TAG: Definition,
}

