from __future__ import unicode_literals
import sys
import collections
import functools
import contextlib
import io
from itertools import tee, chain

from markupsafe import Markup, escape
PY2 = sys.version_info[0] == 2
str_types = basestring if PY2 else (str, )


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


def process_args(args):
    style_args_a = args.get('style', ())
    class_ = args.get('class_', ())

    remaining_args = (item for item in args.items() if item[0] not in ('c', 'style', 'class_'))

    tag_args, style_args_b = partition(remaining_args, lambda i: i[0].startswith('s_'))
    tag_args = ((optimize_attr_name(k), v) for k, v in tag_args)
    tag_args = sorted(tag_args)  # For stability in tests (We want PEP 468!)

    if isinstance(style_args_a, dict):
        style_args_a = style_args_a.items()
    style_args_b = ((k[2:], v) for k, v in style_args_b)
    style = style_join((style_item(optimize_attr_name(k), escape(v)) for k, v in chain(style_args_a, style_args_b)))
    if not isinstance(class_, str_types):
        class_ = class_join(class_)
    tag_args = chain((('class', class_), ('style', style)), tag_args)
    return args_join(k if k in boolean_attrs else args_item(k, escape(v))
                     for k, v in tag_args if v)


class Tag(object):
    __slots__ = ['tag_name', 'contents', 'args', '_empty_tag', '_start_tag', '_end_tag']

    def __init__(self, tag_name, **args):
        self.tag_name = tag_name
        self.contents = args.get('c', None)
        self.args = process_args(args)
        self._start_tag = None
        self._empty_tag = None
        self._end_tag = None

    @property
    def start_tag(self):
        if not self._start_tag:
            if self.args:
                self._start_tag = tag_start_with_args(self.tag_name, self.args)
            else:
                self._start_tag = tag_start(self.tag_name)
        return self._start_tag

    @property
    def empty_tag(self):
        if not self._empty_tag:
            if self.tag_name not in void_tags:
                # HTML5 does not allow self closing empty tag.
                # TODO: Add support to switch between HTML5 and HTML4 modes
                self._empty_tag = self.start_tag + self.end_tag
            else:
                self._empty_tag = self.start_tag
        return self._empty_tag

    @property
    def end_tag(self):
        if not self._end_tag:
            if self.tag_name not in void_tags:
                self._end_tag = tag_end(self.tag_name)
            else:
                self._end_tag = nothing
        return self._end_tag

writer_stack_item = collections.namedtuple('WriterStackItem', ['tag', 'indent_level', 'contents_same_line'])


class TagWriterContext(object):
    __slots__ = ['__enter__', 'write_end_tag']

    def __init__(self, write_start_tag, write_end_tag):
        self.__enter__ = write_start_tag
        self.write_end_tag = write_end_tag

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_end_tag()
        return False


class Writer(object):
    def __init__(self, out_file, indent='  '):
        self.out_file = out_file
        self.stack = collections.deque()
        self.indent = indent
        self.root_stack = writer_stack_item(None, 0, False)
        self._first_line = True
        self._last_write_is_tag = True

    def get_current_stack(self):
        try:
            return self.stack[-1]
        except IndexError:
            return self.root_stack

    def write(self, item, same_line=False, contents_same_line=True):
        if isinstance(item, Tag):
            self.write_tag(item, same_line, contents_same_line)
        elif isinstance(item, (list, tuple)):
            for subitem in item:
                self.write(subitem, same_line, contents_same_line)
        else:
            current_stack = self.get_current_stack()
            self._write_whitespace(current_stack, same_line, False)
            if item is not None:
                self.out_file.write(escape(item))
    __call__ = write

    def write_tag(self, tag, same_line=False, contents_same_line=True):
        current_stack = self.get_current_stack()
        if tag.contents:
            with self.c(tag, same_line, contents_same_line):
                if isinstance(tag.contents, str_types):
                    self.write(tag.contents)
                else:
                    for item in tag.contents:
                        self.write(item)
        else:
            self._write_whitespace(current_stack, same_line, True)
            self.out_file.write(tag.empty_tag)

    def write_start_tag(self, tag, same_line=False, contents_same_line=False):
        current_stack = self.get_current_stack()
        self._write_whitespace(current_stack, same_line, True)
        self.out_file.write(tag.start_tag)
        self.stack.append(writer_stack_item(tag, current_stack.indent_level + 1,
                                            current_stack.contents_same_line or contents_same_line))

    def write_end_tag(self):
        popped_stack = self.stack.pop()
        current_stack = self.get_current_stack()
        if not popped_stack.contents_same_line:
            self.out_file.write('\n{}'.format(self.indent * current_stack.indent_level))
        self._last_write_is_tag = True
        self.out_file.write(popped_stack.tag.end_tag)

    def context(self, tag, same_line=False, contents_same_line=False):
        return TagWriterContext(functools.partial(self.write_start_tag, tag, same_line, contents_same_line),
                                self.write_end_tag)

    c = context

    def _write_whitespace(self, current_stack, same_line, is_tag):
        if not (same_line or current_stack.contents_same_line):
            fmt = '{}' if self._first_line else '\n{}'
            self.out_file.write(fmt.format(self.indent * current_stack.indent_level))
        elif not is_tag and not self._last_write_is_tag:
            self.out_file.write(' ')
        self._first_line = False
        self._last_write_is_tag = is_tag

    @contextlib.contextmanager
    def only_write_if_successful(self):
        old_out_file = self.out_file
        self.out_file = io.StringIO()
        try:
            yield
            old_out_file.write(self.out_file.getvalue())
        finally:
            self.out_file = old_out_file
