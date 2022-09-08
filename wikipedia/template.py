import collections
import logging

from .core import NESTED_TAGS_START, NESTED_TAGS_END


log = logging.getLogger('wikipedia.template')


class Template:

    def __init__(self, name):
        self.name = name
        self.named_params = {}
        self.numbered_params = []

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.named_params.get(
                str(key),
                self.numbered_params[key-1],
            )
        if isinstance(key, slice):
            raise TypeError('Slice not supported!')
        else:
            return self.named_params[key]

    def get(self, key):
        return self.named_params.get(key)

    def __contains__(self, key):
        return key in self.named_params

    def keys(self):
        return self.named_params.keys()

    @classmethod
    def split_params(cls, wikitext):
        start = 0
        nested_level = 0
        for i in range(len(wikitext)):
            sequence = wikitext[i:i+2]
            if sequence in NESTED_TAGS_START:
                nested_level += 1
            elif sequence in NESTED_TAGS_END:
                nested_level -= 1
            if wikitext[i] == '|' and not nested_level:
                yield wikitext[start:i]
                start = i+1
        yield wikitext[start:]

    def parse_params(self, params):
        for param in self.split_params(params):
            name, is_named, value = param.partition('=')
            name = name.strip()
            if is_named:
                value = value.strip()
                if value:
                    self.named_params[name] = value
            else:
                self.numbered_params.append(name)

    @classmethod
    def find_all(cls, content):
        # NOTE: Using deque() so we can push back part of line and parse as new line
        lines = collections.deque(
            line.strip() for line
            in content.splitlines()
            if line.strip()
        )
        lines.reverse()
        template = None
        while lines:
            line = lines.pop()
            if line.startswith('{{'):
                # NOTE: Fix {{template|...}}{{another_template
                end = line.find('}}')
                start = line.find('{{', 1)
                if start > end:
                    lines.append(line[start:])
                    line = line[:start]

                name = line.strip('{}')
                name, has_params, params = name.partition('|')
                template = Template(name)
                if has_params:
                    template.parse_params(params)
            if template:
                if line.startswith('|'):
                    template.parse_params(line[1:])
                elif line.startswith('}}') or line.endswith('}}'):
                    yield template
                    template = None

    def __repr__(self):
        return f'<{self.__class__.__name__} name="{self.name}">'

