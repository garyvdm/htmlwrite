import unittest
import io

from htmlwrite import Tag, Writer

class TestTag(unittest.TestCase):

    def test_no_args(self):
        tag = Tag('div')
        self.assertEqual(tag.start_tag, '<div>')
        self.assertEqual(tag.end_tag, '</div>')
        self.assertEqual(tag.empty_tag, '<div />')

    def test_args(self):
        tag = Tag('div', foo='bar')
        self.assertEqual(tag.start_tag, '<div foo="bar">')
        self.assertEqual(tag.end_tag, '</div>')
        self.assertEqual(tag.empty_tag, '<div foo="bar" />')

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
        tag = Tag('input', type_="checkbox", checked=True)
        self.assertEqual(tag.start_tag, '<input type="checkbox" checked>')

    def test_bool_arg_false(self):
        tag = Tag('input', type_="checkbox", checked=False)
        self.assertEqual(tag.start_tag, '<input type="checkbox">')


class TestWriter(unittest.TestCase):

    def setUp(self):
        self.file = io.StringIO()
        self.writer = Writer(self.file)

    def assertOutputEqual(self, expected):
        self.assertEqual(expected, self.file.getvalue())

    def test_write_str(self):
        self.writer('Hello world <')
        self.assertOutputEqual('Hello world &lt;')

    def test_write_str_2_lines(self):
        self.writer('Hello')
        self.writer('world')
        self.assertOutputEqual('Hello\nworld')

    def test_write_str_2_sameline(self):
        self.writer('Hello')
        self.writer(' world', same_line=True)
        self.assertOutputEqual('Hello world')

    def test_write_empty_tag(self):
        self.writer(Tag('div', c=()))
        self.assertOutputEqual('<div />')

