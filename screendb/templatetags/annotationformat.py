#!/usr/bin/python
# -*- coding: utf-8 -*-

from django import template
from django.template.defaultfilters import stringfilter
from annotationparser import parse, SyntaxError
from re import compile
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()


def annotation_to_li(s, esc):
    """given annotation text, format as nested <li>"""

    # count number of space at the beginning of lineusing this regular
    # expression

    spaces = compile(r'^(\s*)')
    html = ''
    level = 0
    prev_level = 0

    lines = s.split('\n')
    line = ''
    while not line.strip():
        try:
            line = lines.pop(0)
        except:
            break
    if not line:
        return ''
    if ':' in line:
        (key, value) = line.split(':', 1)
    else:
        (key, value) = (line, '')
    level = len(spaces.match(key).group(0))
    try:
        while True:
            if level == prev_level:
                html += \
                    '<li><span class="key">%s</span><span class="value">%s</span></li>' \
                    % (esc(key), esc(value))
                line = ''
                while not line.strip():
                    try:
                        line = lines.pop(0)
                    except:
                        break
                if not line:  # end of file
                    while level != 0:
                        html += '</ul>'
                        level -= 1
                    break
                if ':' in key:
                    (key, value) = line.split(':', 1)
                else:
                    (key, value) = (line, '')
                level = len(spaces.match(key).group(0))
                continue
            elif level > prev_level:
                html += '<ul>'
                prev_level += 1
                continue
            elif level < prev_level:
                html += '</ul>'
                prev_level -= 1
                continue
    except IndexError:
        pass

    return html


def tree_to_li(tree, esc):
    """given a tree returned by annotationparser, generate HTML"""

    html = ''
    for (name, value, subtree) in tree:
        (name, value) = (esc(name), esc(value))
        if subtree:
            html += \
                '<li><span class="key">%s</span><span class="value">%s</span><ul>%s</ul></li>' \
                % (name, value, tree_to_li(subtree, esc))
        else:
            html += \
                '<li><span class="key">%s</span><span class="value">%s</span></li>' \
                % (name, value)
    return html


@stringfilter
def annotation_as_li(value, autoescape=None):
    """
....format annotation text, which could be simple key-value pairs separated
....by linebreaker, or more complicated annotation syntax parsed by 
....annotationparser.py
...."""

    # escaping input if needed

    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    if ',' in value or '{' in value or '}' in value:
        try:
            out = tree_to_li(parse(value), esc)
        except:
            out = 'ANNOTATION WITH BAD SYNTAX'
    elif ':' in value:
        out = annotation_to_li(value, esc)
    else:
        out = esc(value)
    return mark_safe(out)
annotation_as_li.needs_autoescape = True

register.filter('annotation_as_li', annotation_as_li)
