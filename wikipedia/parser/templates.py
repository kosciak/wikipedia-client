import collections
import logging

from .wikitext import WikiText, WikitextIterator


log = logging.getLogger('wikipedia.parser.templates')


# https://en.wikipedia.org/wiki/Help:Template
# https://meta.wikimedia.org/wiki/Help:Template

TEMPLATE_START = '{{'
TEMPLATE_END = '}}'
PARAMETER_SEPARATOR = '|'

NESTED_TAGS_START = {
    '[[',
    '{{',
}

NESTED_TAGS_END = {
    ']]',
    '}}',
}


class Template:

    def __init__(self, name):
        self.name = name
        self.named_params = {}
        self.numbered_params = []
        self.__last_param = None

    def __getitem__(self, key):
        # See: https://meta.wikimedia.org/wiki/Help:Template#Mix_of_named_and_unnamed_parameters
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

    def _append_to_last_param(self, value):
        if self.__last_param is None:
            return
        last_value = self[self.__last_param]
        if last_value:
            value = f'{last_value}\n{value}'
            value = WikiText(last_value, value)
        if str(self.__last_param) in self.named_params:
            self.named_params[self.__last_param] = value
        else:
            self.numbered_params[self.__last_param-1] = value

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
            if wikitext[i] == PARAMETER_SEPARATOR and not nested_level:
                yield wikitext[start:i]
                start = i+1
        yield wikitext[start:]

    def parse_params(self, params):
        for param in self.split_params(params):
            name, is_named, value = param.partition('=')
            name = name.strip()
            if is_named:
                value = WikiText(value.strip())
                if value:
                    self.named_params[name] = value
                    self.__last_param = name
            else:
                self.numbered_params.append(WikiText(name))
                self.__last_param = len(self.numbered_params)

    @classmethod
    def find_all(cls, wikitext):
        template = None
        lines = WikitextIterator(wikitext, strip=True, empty=False)
        for line in lines:

            inline_template = False
            if (template is None) and line.startswith(TEMPLATE_START):
                # Fix for: {{template|...}}{{another_template
                #          {{template|...}} text {{another_template|...}}
                end = line.find(TEMPLATE_END)
                start = line.find(TEMPLATE_START, 1)
                if start > end:
                    if end > 0:
                        # NOTE: In reverse order!
                        lines.push(
                            line[end+2:start],
                            line[start:],
                        )
                        line = line[:end+2]
                    else:
                        lines.push(line[start:])
                        line = line[:start]

                # TODO: Might still fail with something like: {{template|name={{value|...}}
                #       and continuation of params on next line
                name = line.strip('{}')
                name, has_params, params = name.partition(PARAMETER_SEPARATOR)
                template = Template(name)
                inline_template = True
                if has_params:
                    template.parse_params(params)

            if template:
                if line.startswith(PARAMETER_SEPARATOR):
                    # Start of parameter(s)
                    template.parse_params(line[1:])
                elif line.startswith(TEMPLATE_END):
                    # End of template, rest of the line should be parsed
                    yield template
                    template = None
                    lines.push(line[2:])
                elif inline_template and line.endswith(TEMPLATE_END):
                    # Only for inline templates that start and end on same line
                    # TODO: Might still fail with something like: {{template|name={{value|...}}
                    #       and continuation of params on next line
                    yield template
                    template = None
                elif template.named_params or template.numbered_params:
                    # Line is a continuation of last parsed param
                    # https://pl.wikipedia.org/wiki/Wis%C5%82a
                    # https://pl.wikipedia.org/wiki/Ciechocinek
                    template._append_to_last_param(line)

    def __repr__(self):
        return f'<{self.__class__.__name__} name="{self.name}">'

