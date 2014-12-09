import collections
import functools
from itertools import tee, chain

from markupsafe import Markup, escape


def partition(items, predicate=bool):
    a, b = tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if not pred),
            (item for pred, item in b if pred))


def optimize_attr_name(name):
    while name.endswith("_"):
        name = name[:-1]
    name = name.replace("_", "-")
    return name

tag_start = Markup('<{}>')
tag_start_with_args = Markup('<{} {}>')
tag_empty_start = Markup('<{} />')
tag_empty_start_with_args = Markup('<{} {} />')
tag_end = Markup('</{}>')

style_item = Markup('{}: {};').format
style_join = Markup(' ').join
class_join = Markup(' ').join
args_item = Markup('{}="{}"').format
args_join = Markup(' ').join


class Tag(object):
    __slots__ = ['tag_name', 'contents', 'args', '_empty_tag', '_start_tag', '_end_tag']

    def __init__(self, tag_name, **args):
        self.tag_name = tag_name

        self.contents = args.pop('c', None)
        style_args_a = args.pop('style', ())
        class_ = args.pop('class_', ())
        tag_args, style_args_b = partition(args.items(), lambda i: i[0].startswith('s_'))
        tag_args = ((optimize_attr_name(k), v) for k, v in tag_args)

        if isinstance(style_args_a, dict):
            style_args_a = style_args_a.items()
        style_args_b = ((k[2:], v) for k, v in style_args_b)
        style_args = ((optimize_attr_name(k), v) for k, v in chain(style_args_a, style_args_b))
        style = style_join((style_item(*item) for item in style_args))
        class_ = class_join(class_)
        tag_args = chain(tag_args, (('style', style), ('class', class_)))
        tag_args = (arg for arg in tag_args if arg[1])
        self.args = args_join(args_item(*item) for item in tag_args)

        self._start_tag = None
        self._empty_tag = None
        self._end_tag = None

    @property
    def start_tag(self):
        if not self._start_tag:
            if self.args:
                self._start_tag = tag_start_with_args.format(self.tag_name, self.args)
            else:
                self._start_tag = tag_start.format(self.tag_name)
        return self._start_tag

    @property
    def empty_tag(self):
        if not self._empty_tag:
            if self.args:
                self._empty_tag = tag_empty_start_with_args.format(self.tag_name, self.args)
            else:
                self._empty_tag = tag_empty_start.format(self.tag_name)
        return self._empty_tag

    @property
    def end_tag(self):
        if not self._end_tag:
            self._end_tag = tag_end.format(self.tag_name)
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

    def write(self, item, same_line=False, contents_same_line=False):
        if isinstance(item, Tag):
            if item.contents is None:
                return self.wrapped(item, same_line, contents_same_line)
            else:
                self.write_tag(item, same_line, contents_same_line)
        else:
            current_stack = self.get_current_stack()
            self._write_whitespace(current_stack, same_line, False)
            self.out_file.write(escape(item))

    __call__ = write

    def write_tag(self, tag, same_line=False, contents_same_line=False):
        if tag.contents:
            with self.wrapped(tag, same_line, contents_same_line):
                for item in tag.contents:
                    self.write(item)
        else:
            current_stack = self.get_current_stack()
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

    def wrapped(self, tag, same_line=False, contents_same_line=False):
        return TagWriterContext(functools.partial(self.write_start_tag, tag, same_line, contents_same_line),
                                self.write_end_tag)

    def _write_whitespace(self, current_stack, same_line, is_tag):
        if not same_line or current_stack.contents_same_line:
            fmt = '{}' if self._first_line else '\n{}'
            self.out_file.write(fmt.format(self.indent * current_stack.indent_level))
        elif not is_tag and self._last_write_is_tag:
            self.out_file.write(' ')
        self._first_line = False
        self._last_write_is_tag = is_tag
