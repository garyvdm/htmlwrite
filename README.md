`htmlwrite` is a python library for writing html to a file like object, using a pythonic syntax.  Use as an alternative to templating engines. 

    >>> import sys
    >>> 
    >>> from htmlwrite import Writer, Tag
    >>> 
    >>> writer = Writer(sys.stdout)
    >>> w = writer.write
    >>> c = writer.context
    >>> 
    >>> with c(Tag('html')):
    ...     with c(Tag('body')):
    ...         with c(Tag('div', class_=('foo', ), s_font_weight='bold')):
    ...             w('Hello world  ')
    ...         w(Tag('div', c=('ok, bye.', )))
    ... 
    <html>
      <body>
        <div class="foo" style="font-weight: bold;">
          Hello world  
        </div>
        <div>ok, bye.</div>
      </body>
    </html>

