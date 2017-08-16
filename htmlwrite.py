from __future__ import unicode_literals


from collections import deque, Iterable, Mapping, namedtuple
from contextlib import contextmanager
from functools import partial
from io import StringIO
from itertools import chain, tee
from sys import version_info

import cachetools.func

from markupsafe import escape, Markup

PY2 = version_info[0] == 2
str_types = basestring if PY2 else (str, )  # NOQA


def partition(items, predicate=bool):
    a, b = tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if not pred),
            (item for pred, item in b if pred))


def optimize_attr_name(name):
    while name.endswith('_'):
        name = name[:-1]
    name = name.replace('_', '-')
    return name


tag_start = '<{}>'.format
tag_start_with_args = '<{} {}>'.format
tag_empty_start = '<{} />'.format
tag_empty_start_with_args = '<{} {} />'.format
tag_end = '</{}>'.format

style_item = '{}: {};'.format
style_join = ' '.join
class_join = ' '.join
args_item = '{}="{}"'.format
args_join = ' '.join

nothing = Markup('')

boolean_attrs = {
    'checked',
    'defer',
    'disabled',
    'multiple',
    'readonly',
    'selected',
}

void_tags = {
    'area',
    'base',
    'basefont',
    'br',
    'col',
    'frame',
    'hr',
    'img',
    'input',
    'isindex',
    'link',
    'meta',
    'param',
}

non_self_closing_tags = {
    'script',
    'span',
    'a',
}


@cachetools.func.lru_cache(2048)
def _start_tag(tag_name, style, class_, args):
    tag_args, style_from_args = partition(args, lambda i: i[0].startswith('s_'))
    tag_args = ((optimize_attr_name(k), v) for k, v in tag_args)

    style_from_args = ((k[2:], v) for k, v in style_from_args)
    style = style_join((style_item(optimize_attr_name(k), escape(v)) for k, v in chain(style, style_from_args)))
    if not isinstance(class_, str_types) and isinstance(class_, Iterable):
        class_ = class_join(class_)
    tag_args = chain((('class', class_), ('style', style)), tag_args)
    args_html = args_join(k if k in boolean_attrs else args_item(k, escape(v))
                          for k, v in tag_args if v)
    if args_html:
        return tag_start_with_args(tag_name, args_html)
    else:
        return tag_start(tag_name)


class Tag(object):
    __slots__ = ['tag_name', 'contents', 'style', 'class_', 'args', ]

    def __init__(self, tag_name, c=None, style=(), class_=(), **args):
        self.tag_name = tag_name
        self.contents = c
        # Freeze args to "immutable" hashable types so that tag methods can be cached
        # Sort the dict items for stability in tests (We want PEP 468!)
        self.args = tuple(sorted(args.items()))
        if isinstance(style, Mapping):
            self.style = tuple(style.items())
        elif not isinstance(style, str_types) and isinstance(style, Iterable) and not isinstance(style, tuple):
            self.style = tuple(style)
        else:
            self.style = style

        if not isinstance(class_, str_types) and isinstance(class_, Iterable):
            self.class_ = tuple(class_)
        else:
            self.class_ = class_

    @property
    def start_tag(self):
        return _start_tag(self.tag_name, self.style, self.class_, self.args)

    @property
    def empty_tag(self):
        if self.tag_name not in void_tags:
            # HTML5 does not allow self closing empty tag.
            # TODO: Add support to switch between HTML5 and HTML4 modes
            return self.start_tag + self.end_tag
        else:
            return self.start_tag

    @property
    def end_tag(self):
        if self.tag_name not in void_tags:
            return tag_end(self.tag_name)
        else:
            return nothing


writer_stack_item = namedtuple('WriterStackItem', ['tag', 'indent_level', 'contents_same_line', 'child_same_line'])


class TagWriterContext(object):
    __slots__ = ['__enter__', 'write_end_tag']

    def __init__(self, writer, tag, child_same_line=False, contents_same_line=False, indent=True):
        self.__enter__ = partial(writer.write_start_tag, tag, child_same_line, contents_same_line, indent=indent)
        self.write_end_tag = partial(writer.write_end_tag, indent=indent)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_end_tag()
        return False


class Writer(object):
    def __init__(self, out_file, indent='  '):
        self.out_file = out_file
        self.stack = deque()
        self.indent = indent
        self.root_stack = writer_stack_item(None, 0, False, False)
        self._current_line_indent_written = False
        self._last_write_is_tag = True

    def get_current_stack(self):
        try:
            return self.stack[-1]
        except IndexError:
            return self.root_stack

    def write(self, item, next_same_line=False, contents_same_line=True, indent=True):
        if isinstance(item, Tag):
            self.write_tag(item, next_same_line, contents_same_line)
        elif not isinstance(item, str_types) and isinstance(item, Iterable):
            for subitem in item:
                self.write(subitem, next_same_line, contents_same_line)
        else:
            current_stack = self.get_current_stack()
            self._write_start_whitespace(current_stack.indent_level, False, indent)
            if item is not None:
                self.out_file.write(escape(item))
            self._write_end_whitespace(current_stack.contents_same_line or next_same_line)

    __call__ = write
    w = write

    def write_tag(self, tag, same_line=False, contents_same_line=True, indent_contents=True, indent_tag=True):
        if tag.contents:
            with self.c(tag, same_line, contents_same_line, indent=indent_tag):
                if isinstance(tag.contents, str_types):
                    self.write(tag.contents, indent=indent_contents)
                else:
                    for item in tag.contents:
                        self.write(item, indent=indent_contents)
        else:
            prev_stack = self.get_current_stack()
            self._write_start_whitespace(prev_stack.indent_level, True, indent=indent_tag)
            self.out_file.write(tag.empty_tag)
            self._write_end_whitespace(prev_stack.contents_same_line or contents_same_line or same_line)

    def write_start_tag(self, tag, child_same_line=False, contents_same_line=False, indent=True):
        prev_stack = self.get_current_stack()
        new_stack = writer_stack_item(
            tag,
            prev_stack.indent_level + 1 if not child_same_line else prev_stack.indent_level,
            prev_stack.contents_same_line or contents_same_line,
            child_same_line)
        self.stack.append(new_stack)

        self._write_start_whitespace(prev_stack.indent_level, True, indent=indent)
        self.out_file.write(tag.start_tag)
        self._write_end_whitespace(prev_stack.contents_same_line or contents_same_line or child_same_line)

    def write_end_tag(self, indent=True, next_same_line=False):
        popped_stack = self.stack.pop()
        current_stack = self.get_current_stack()
        self._write_start_whitespace(current_stack.indent_level, True, indent=indent)
        self._last_write_is_tag = True
        self.out_file.write(popped_stack.tag.end_tag)
        self._write_end_whitespace(current_stack.contents_same_line or next_same_line or current_stack.child_same_line)

    def context(self, tag, child_same_line=False, contents_same_line=False, indent=True):
        return TagWriterContext(self, tag, child_same_line, contents_same_line, indent)

    c = context

    def _write_start_whitespace(self, indent_level, is_tag, indent=True):
        if not self._current_line_indent_written:
            indent_level = indent_level if indent else 0
            self.out_file.write(self.indent * indent_level)
            self._current_line_indent_written = True
        elif not is_tag and not self._last_write_is_tag:
            self.out_file.write(' ')
        self._last_write_is_tag = is_tag

    def _write_end_whitespace(self, same_line):
        if not same_line:
            self.out_file.write('\n')
            self._current_line_indent_written = False

    @contextmanager
    def only_write_if_successful(self):
        old_out_file = self.out_file
        self.out_file = StringIO()
        try:
            yield
            old_out_file.write(self.out_file.getvalue())
        finally:
            self.out_file = old_out_file
