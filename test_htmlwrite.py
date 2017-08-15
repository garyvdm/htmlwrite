from __future__ import unicode_literals

import doctest
import io
import unittest

from htmlwrite import Tag, Writer


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocFileSuite('README.md'))
    return tests


class TestTag(unittest.TestCase):

    def test_no_args(self):
        tag = Tag('div')
        self.assertEqual(tag.start_tag, '<div>')
        self.assertEqual(tag.end_tag, '</div>')
        self.assertEqual(tag.empty_tag, '<div></div>')

    def test_void_tag(self):
        tag = Tag('br')
        self.assertEqual(tag.start_tag, '<br>')
        self.assertEqual(tag.end_tag, '')
        self.assertEqual(tag.empty_tag, '<br>')

    def test_non_self_closing_tag(self):
        tag = Tag('script')
        self.assertEqual(tag.empty_tag, '<script></script>')

    def test_args(self):
        tag = Tag('div', foo='bar')
        self.assertEqual(tag.start_tag, '<div foo="bar">')
        self.assertEqual(tag.end_tag, '</div>')
        self.assertEqual(tag.empty_tag, '<div foo="bar"></div>')

    def test_style(self):
        tag = Tag('div', style={'foo': 'bar'}, s_moo='cow')
        self.assertEqual(tag.start_tag, '<div style="foo: bar; moo: cow;">')

    def test_style_list(self):
        tag = Tag('div', style=[('foo', 'bar')])
        self.assertEqual(tag.start_tag, '<div style="foo: bar;">')

    def test_class_list(self):
        tag = Tag('div', class_=['foo', 'bar'])
        self.assertEqual(tag.start_tag, '<div class="foo bar">')

    def test_class_str(self):
        tag = Tag('div', class_='foo')
        self.assertEqual(tag.start_tag, '<div class="foo">')

    def test_bool_arg_true(self):
        tag = Tag('input', checked=True, type_="checkbox")
        self.assertEqual(tag.start_tag, '<input checked type="checkbox">')

    def test_bool_arg_false(self):
        tag = Tag('input', checked=False, type_="checkbox")
        self.assertEqual(tag.start_tag, '<input type="checkbox">')


class TestWriter(unittest.TestCase):

    def setUp(self):
        self.file = io.StringIO()
        self.writer = Writer(self.file)

    def assertOutputEqual(self, expected):
        self.assertEqual(expected, self.file.getvalue())

    def test_write_str(self):
        self.writer('Hello world <')
        self.assertOutputEqual('Hello world &lt;\n')

    def test_write_str_2_lines(self):
        self.writer('Hello')
        self.writer('world')
        self.assertOutputEqual('Hello\nworld\n')

    def test_write_list(self):
        self.writer(['Hello', 'world'])
        self.assertOutputEqual('Hello\nworld\n')

    def test_write_str_2_same_line(self):
        self.writer('Hello', next_same_line=True)
        self.writer('world', next_same_line=True)
        self.assertOutputEqual('Hello world')
        # Note that a space is automatically written.

    def test_write_empty_tag(self):
        self.writer(Tag('div'))
        self.assertOutputEqual('<div></div>')

    def test_write_tag_with_str_contents(self):
        self.writer(Tag('div', c='Hello world'))
        self.assertOutputEqual('<div>Hello world</div>\n')

    def test_write_tag_with_list_contents(self):
        self.writer(Tag('div', c=[
            'Hello world',
            Tag('foo')
        ]))
        self.assertOutputEqual('<div>Hello world<foo></foo></div>\n')

    def test_write_tag_with_not_contents_same_line(self):
        self.writer(Tag('div', c=['Hello', 'world']), contents_same_line=False)
        self.assertOutputEqual(
            '<div>\n'
            '  Hello\n'
            '  world\n'
            '</div>\n'
        )

    def test_tag_context(self):
        with self.writer.c(Tag('div')):
            self.writer('Hello world')
        self.assertOutputEqual(
            '<div>\n'
            '  Hello world\n'
            '</div>\n'
        )

    def test_tag_context_no_indent(self):
        with self.writer.c(Tag('div')):
            self.writer('Hello world', indent=False)
        self.assertOutputEqual(
            '<div>\n'
            'Hello world\n'
            '</div>\n'
        )

    def test_tag_context_tag_no_indent(self):
        with self.writer.c(Tag('div')):
            self.writer.write_tag(Tag('span', c='Hello world'), indent_tag=False)
        self.assertOutputEqual(
            '<div>\n'
            '<span>Hello world</span>\n'
            '</div>\n'
        )

    def test_tag_context_tag_content_no_indent(self):
        with self.writer.c(Tag('div')):
            self.writer.write_tag(Tag('span', c='Hello world'), indent_contents=False, contents_same_line=False)
        self.assertOutputEqual(
            '<div>\n'
            '  <span>\n'
            'Hello world\n'
            '  </span>\n'
            '</div>\n'
        )

    def test_tag_same_line(self):
        with self.writer.c(Tag('div'), child_same_line=True):
            with self.writer.c(Tag('span')):
                self.writer('Hello world')
        self.assertOutputEqual(
            '<div><span>\n'
            '  Hello world\n'
            '</span></div>\n'
        )
