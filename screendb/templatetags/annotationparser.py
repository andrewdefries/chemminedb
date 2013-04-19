#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
A simple parser to parse the key-value pair in the compound description.

Return:
....a tree having each node represented in a tuple havin this form:
....(name, value, children)

Format:
....EXAMPLES:
........1. key1: value1
........2. key1: value1 , key2 : value2
........3. key1: value1 { subkey1: subvalue1 }
........4. key1: value1 { subkey1: subvalue1, subkey1: subv2}
........5. key1: { subkey1: subvalue1}

....* keywords are comma (,), {, }, and :. We do not support to include
....  them in the key or value now.
....* newlines, tabs are spaces are ignored when they are used as
....  separator. They are allowed in key and value
....* values can be a nested dictionary. Nested dictionary must be
....  anonymous. e.g.
....  name: value, {nested_key: nested_value}
....  You can, however, do this
....  name: {nested_key: nested_value}
....  which just sets the value to empty
....* quoting is enclosed in ''' and '''. quoting can be embedded into
....  other text. For example, blahblah'''quoted'''blah is allowd.
....
Future work:
....* add support for multiple quotes in value
....* add validation function to detect badly-formatted strings
........* How to detect error:
............1. cannot find start
............2. cannot find end
............Define exception class. Print remaining
"""

import re
import string
import pdb

separator = ''


class SyntaxError(Exception):

    """SyntaxError excpetion. The only information contained is the string
offset, and some simple description"""

    def __init__(self, offset, description=''):
        self.offset = offset
        self.description = description

    def __str__(self):
        return 'Syntax error near position ' + str(self.offset) + ': ' \
            + self.description


def parse(desc_string, parent=None):

    # key_pattern eats only the pair key, so the value can be an
    # embedded pairs in '{}' or quoting
    # Align points: first non-empty non-keyword character, colon sign
    # stop point: first appearance of colon sign
    # .s.p.a.c.e.s...K.E.Y*...:

    key_pattern = \
        re.compile(r"""
			(?:[ \t\r\n,])*			# leading spaces
			([^ \t\r\n,\{\}:][^,\{\}:]*?)	# the key; non-greedy
			(?:[ \t\r\n])*			# trailing spaces
			:				# separator
			"""
                   , re.VERBOSE)

    # value_pattern eats value
    # align points: first non-empty non-keyword character
    # stop point: first appearance of keywords

    value_pattern = \
        re.compile(r"""
			(?:[ \t\r\n])*			# leading spaces of value
			([^ \t\r\n,\{\}:][^,\{\}:]*)	# value, non-greedy won't work here
			(?: [ \t\r\n])*			# trailing spaces # unnecessary?
			,?				# optional separator
			"""
                   , re.VERBOSE)
    value_pattern2 = \
        re.compile(r"""
			(?:[ \t\r\n])*			# leading spaces of value
			([^ \t\r\n,\{\}:][^,\{\}:]*)	# value, non-greedy won't work here
			(?: [ \t\r\n])*			# trailing spaces # unnecessary?
			,?				# might have a ',' here
			(?: [ \t\r\n])*			# trailing spaces # unnecessary?
			{				# start embedded
			"""
                   , re.VERBOSE)

    # quoted_value_pattern
    # Align points: first ''' and second '''
    # stop point: first appearance of keyword after the second '''

    quoted_value_pattern = \
        re.compile(r"""
			(?:[ \t\r\n,])*		# leading spaces
			([^,\{\}:]*?)		# leading content, non-greedy
			'''
			(.*?)			# use non-greeding
			'''
			([^,\{\}:]*)		# trailing content
			(?:[ \t\r\n,])*		# trailing spaces
			,?			# optional separator
			"""
                   , re.VERBOSE | re.DOTALL)

    # end_pattern expects a compulsory '}'
    # align point: must be a }

    end_pattern = re.compile(r"(?:[ \t\r\n])*\}")
    start_pattern = re.compile(r"(?:[ \t\r\n])*\{")

    # error_pattern: use to detect name pattern error

    error_pattern = re.compile(r"[ \t\r\n]*[a-zA-Z]")

    pos = 0
    if parent is None:
        entries = []

    if parent is not None:

        # for non-top level, we expect the whole string to be in a pair of embraces

        match = start_pattern.match(desc_string, pos)
        if match is None:
            raise SyntaxError(pos, 'cannot find { or value syntax error'
                              )
        pos = match.end()

    while True:

        # extract the key

        match = key_pattern.match(desc_string, pos)
        if match is None:
            if error_pattern.match(desc_string, pos):
                raise SyntaxError(pos,
                                  'cannot find the start of a name-value pair: no name pattern found'
                                  )
            break
        pos = match.end()
        key = match.group(1).rstrip()

        # extract the value

        for pattern in [quoted_value_pattern, value_pattern2,
                        value_pattern, None]:

            # last resort: try recurssion with empty value ( key:  { ...)

            if pattern is None:
                entry = (key, '', [])
                if parent is not None:
                    parent.append(entry)
                else:
                    entries.append(entry)

                # now try the embedded part

                try:
                    offset = parse(desc_string[pos:], entry[2])
                    pos = pos + offset
                except SyntaxError, exception:
                    raise SyntaxError(exception.offset + pos,
                            exception.description)
                break

            # for normal key extraction

            match = pattern.match(desc_string, pos)
            if match is not None:
                entry = (key, string.join(match.groups(),
                         separator).rstrip(), [])
                if parent is not None:
                    parent.append(entry)
                else:
                    entries.append(entry)
                pos = match.end()
                if pattern == value_pattern2:
                    pos = pos - 1

                    # with embedded string

                    try:
                        offset = parse(desc_string[pos:], entry[2])
                        pos = pos + offset
                    except SyntaxError, exception:
                        raise SyntaxError(exception.offset + pos,
                                exception.description)
                break

    if parent is not None:
        match = end_pattern.match(desc_string, pos)
        if match is None:
            raise SyntaxError(pos, 'cannot find }')
        pos = match.end()
        return pos
    else:
        return entries


def reverse_parse(trees, indent=0):
    text = ''
    if type(trees[0]) is list or type(trees[0]) is tuple:
        for tree in trees:
            text = text + reverse_parse(tree)
        return text
    (name, value, subtrees) = trees[:3]
    text = text + '\t' * indent + '%s : %s,' % (name, value) + '\n'
    if subtrees and subtrees is not None:
        text = text + '\t' * indent + '{' + '\n'
        for subtree in subtrees:
            text = text + reverse_parse(subtree, indent + 1)
        text = text + '\t' * indent + '}\n'
    return text


def dump_tree(trees, indent=0):
    for (name, value, subtree) in trees:
        print '\t' * indent + '[%s : %s]' % (name, value)
        if subtree:
            dump_tree(subtree, indent + 1)


if __name__ == '__main__':
    desc = 'name'
    desc2 = \
        """
	Research Goal: Elucidate networks of genes that control vesicular trafficking Arabidopsis,
Forward Screen:yes, {
	Target Pathway or Process : '''vesicular trafficking, auxin transport, cell elongation''',
	Organism : Arabidopsis thaliana	,
	Ecotype : Columbia (Col0), 
	Genotype : PIN2'''::'''PIN2-GFP,
	Tissue and/or Cell Type(s): '''Root tip, epidermal and cortex cells''',
	Transgene:PIN2_ARATH '''(URL: http://www.pir.uniprot.org/cgi-bin/upEntry?id=PIN2_ARATH)	''',
	Sample Age:4 to 5 days,
	Growth (Culture) Conditions: '''light 16hrs 22.5C, night 8hrs 21C, on MS medium + 1% sucrose'''
},
test embedding: {
	subkey:subvalue
},
List of Screened CMP Libraries:'''Microsource Spectrum, Sigma-TimTec Myria Screen'''
	"""

    print 'Test Case(s):'
    print 'INPUT: %s' % desc2
    try:
        tree = parse(desc2)
    except SyntaxError, inst:
        print inst.description + ':: pos = ' + str(inst.offset)
        print desc[inst.offset:]
    else:
        dump_tree(tree)
        reverse_parse(tree)
