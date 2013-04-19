#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.db import models
from django.db import connection
from django.contrib.auth.models import User
from compounddb.models import *
from time import time
import logging
import re
import os
from django.core.cache import cache
from searchd import WORK_DIR, mydir
from pickle import dump, load
from django.db.models import Q


class SearchError(Exception):

    pass


def add_properties(matches):
    """given matches from annotation search, this function insert properties
....into the result. The input matches is a list of list in this format:
........[search_field, results, more_result?]
....the output modifies <results> into a tuple
........(result, properties)
...."""

    all_compounds = []
    for i in matches:
        all_compounds.extend(list(i[1]))
    lookup = dict()
    for i in \
        Property.objects.filter(compound__in=all_compounds).values_list('compound'
            , 'field', 'value'):
        lookup['%s:%s' % (i[0], i[1])] = i[2]

    from views import all_property_fields
    new_matches = []
    for i in matches:
        results = []
        for c in i[1]:
            properties = []
            for f in all_property_fields():
                key = '%s:%s' % (c.id, f.id)
                properties.append(lookup.get(key, ''))
            results.append((c, properties))
        new_matches.append((i[0], results, i[2]))
    return new_matches


def add_libname(base_queryset):
    return base_queryset.extra(select={'libname': '''select compounddb_libraryheader.name from
		compounddb_libraryheader, compounddb_library,
		compounddb_compound_library where compounddb_libraryheader.id
		=compounddb_library.header_id and
		compounddb_library.id=compounddb_compound_library.library_id and
		compounddb_compound_library.compound_id=compounddb_compound.id order by
		compounddb_library.id desc limit 1'''})


def add_molecular_weight(base_queryset):
    """add MW info from joelib"""

    mw = PropertyField.objects.get(name='MW').id
    return base_queryset.extra(select={'mw': '''select compounddb_property.value from
		compounddb_property where
		compounddb_property.field_id = %s and
		compounddb_property.compound_id = compounddb_compound.id'''},
                               select_params=(mw, ))


def do_library_search(base_queryset, library):
    if isinstance(library, list) or isinstance(library, tuple):
        return base_queryset.filter(library__in=library)
    else:
        return base_queryset.filter(library=library)


def do_annotation_search(base_queryset, query, field):
    query = query.strip()

    if field == 'cid':
        query = query.strip('*')
        base_queryset = base_queryset.filter(cid__icontains=query)
    elif field == 'name':

        base_queryset = \
            base_queryset.extra(where=['compounddb_compound_info_index_col @@ to_tsquery(%s)'
                                ], params=["'" + query + "'"
                                ]).order_by()
    elif field == 'annotation':

        # use full text search in PostgreSQL

        base_queryset = \
            base_queryset.extra(tables=['compounddb_annotation'],
                                where=['compounddb_annotation.compound_id = compounddb_compound.id'
                                ,
                                'compounddb_annotation.search_index_col @@ to_tsquery(%s)'
                                ], params=["'" + query + "'"
                                ]).order_by()
    elif field == 'plate':

        base_queryset = base_queryset.filter(plate__plate__iexact=query)
    elif field == 'well':

        base_queryset = base_queryset.filter(plate__well__iexact=query)

    return base_queryset


def do_paging(base_queryset, limit=50, batch=0):
    offset = batch * limit
    stop = offset + limit + 1  # fetch one more to see if there is more
    compounds = base_queryset[offset:stop]
    more = len(compounds) == limit + 1
    return (compounds[:limit], more)


def do_property_search(
    base_queryset,
    field_name,
    operator,
    value,
    cache_life=3600,
    ):

    field_name = field_name.replace('__', ' ')
    try:
        field = PropertyField.objects.get(name__iexact=field_name)
    except:
        raise SearchError('Unknown property: ' + field_name)

    try:
        value = float(value)
    except ValueError:
        raise SearchError('Invalid number format: ' + value)

    if field.is_integer:
        try:
            value = int(value)
        except ValueError:
            raise SearchError('Expect integer but get ' + value)

    if operator.strip() == '>':
        return base_queryset.filter(property__field=field,
                                    property__value__gt=value)
    if operator.strip() == '=':
        if not field.is_integer:
            raise SearchError('Only integer property supports "=" query. Try ">" or "<"'
                              )
        return base_queryset.filter(property__field=field,
                                    property__value=value)
    if operator.strip() == '<':
        return base_queryset.filter(property__field=field,
                                    property__value__lt=value)
    else:
        raise SearchError('Invalie operator: %s. Only "=", "<" or ">" are supported'
                           % operator)


property_clause = re.compile(r"([a-z0-9-_]+)\s*([><=])\s*([0-9.-]+)")
in_clause = re.compile(r"in\s*:\s*([a-z]+)")
library_clause = re.compile(r"library\s*:\s*([,a-z-_ ]+)")
plate_clause = re.compile(r"plate\s*:\s*([^ ]+)")
well_clause = re.compile(r"well\s*:\s*([^ ]+)")


def search(query, page=1, request=None):
    from compounddb.views import get_library_by_name, \
        fuzzy_get_library_by_name
    matches = []
    query = query.strip().lower()
    base_queryset = Compound.objects

    # limit searches to compounds uploaded by current user, or with blank names

    if request:
        base_queryset = \
            base_queryset.filter(Q(username=request.user.username)
                                 | Q(username=''))
    else:
        base_queryset = base_queryset.filter(username='')

    # check property query

    while True:
        m = property_clause.search(query)
        if not m:
            break
        base_queryset = do_property_search(base_queryset, *m.groups())
        query = query[:m.start()] + query[m.end():]

    field = ['name', 'annotation', 'plate', 'well']

    # check for plate and well

    (plate, well) = (None, None)
    m = plate_clause.search(query)
    if m:
        plate = m.group(1)
        query = query[:m.start()] + query[m.end():]
    m = well_clause.search(query)
    if m:
        well = m.group(1)
        query = query[:m.start()] + query[m.end():]

    # check for "in:" clause

    m = in_clause.search(query)
    if m:
        f = m.group(1)
        if f in field:
            field = [f]
        query = query[:m.start()] + query[m.end():]

    # check for "library:" clause

    library = None
    m = library_clause.search(query)
    if m:
        lib = m.group(1).strip()
        try:
            library = get_library_by_name(lib)
        except:
            try:
                library = fuzzy_get_library_by_name(lib)
                if request:
                    request.user.message_set.create(message='%s does not match name of any library. %s is used instead'
                             % (lib, library.header.name))
            except:
                raise SearchError('No such library: ' + lib)
        query = query[:m.start()] + query[m.end():]
    query.replace(',', '')

    # however, if query has '*', then only search cid

    if '*' in query:
        field = ['cid']

    # add libname

    base_queryset = add_libname(base_queryset)

    # add library criteria

    if library:
        base_queryset = do_library_search(base_queryset, library)

    # add plate/well

    if plate:
        base_queryset = do_annotation_search(base_queryset, plate,
                'plate')
    if well:
        base_queryset = do_annotation_search(base_queryset, well, 'well'
                )

    # now do search

    if query.strip():
        for f in field:
            qs = do_annotation_search(base_queryset, query, f)
            (match, more) = do_paging(qs, batch=page - 1)
            matches.append([f, match, more])
    else:
        (match, more) = do_paging(base_queryset, batch=page - 1)
        matches.append(['general', match, more])
    matches = add_properties(matches)
    return (query, matches)


def do_structure_search(base_queryset, sdf):
    return base_queryset.extra(tables=['compounddb_sdffile'],
                               where=['compounddb_sdffile.compound_id = compounddb_compound.id'
                               ,
                               'compounddb_sdffile.descriptor is not null'
                               ],
                               select={'s': '''select sim(compounddb_sdffile.descriptor, (select ap(%s)))'''
                               }, select_params=[sdf]).order_by('-s')


def struct_search(sdf, library):
    base_queryset = Compound.objects

    # add libname

    base_queryset = add_libname(base_queryset)

    # add library criteria

    if library:
        base_queryset = do_library_search(base_queryset, library)
    base_queryset = do_structure_search(base_queryset, sdf)
    return base_queryset[:30]


class AsyncStructSearchNotReady(Exception):

    pass


class AsyncStructSearchDoesNotExist(Exception):

    pass


def async_struct_search(
    hash,
    sdf,
    library,
    search_term,
    cache_time=15 * 60,
    ):

    workdir = os.path.join(WORK_DIR, hash)
    from shutil import rmtree
    from stat import ST_MTIME
    from time import time
    from subprocess import Popen
    if os.path.exists(workdir):
        if os.path.isdir(workdir):
            if time() - os.stat(workdir)[ST_MTIME] < cache_time:
                logging.info('reusing existing result')
                return
            else:
                rmtree(workdir)
        else:
            logging.warning('working directory can have been polluted')
            logging.warning('removing regular file %s' % workdir)
            os.unlink(workdir)
    os.mkdir(workdir)
    f = file(os.path.join(workdir, 'in'), 'w')
    dump((sdf, library), f)
    f.close()
    f = file(os.path.join(workdir, 'query'), 'w')
    dump(search_term, f)
    f.close()
    cmd = os.path.join(mydir, 'searchd.py') + ' ' + hash
    Popen(cmd, close_fds=True, shell=True)
    return


def load_async_struct_search_result(hash):
    workdir = os.path.join(WORK_DIR, hash)
    if not os.path.exists(workdir):
        raise AsyncStructSearchDoesNotExist
    try:
        f = file(os.path.join(workdir, 'out'))
    except:
        raise AsyncStructSearchNotReady
    compounds = load(f)
    f.close()
    fake_matches = [['', compounds, '']]
    compounds = add_properties(fake_matches)[0][1]
    f = file(os.path.join(workdir, 'query'))
    query = load(f)
    f.close()
    return (compounds, query)


