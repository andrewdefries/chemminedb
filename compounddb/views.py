#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.shortcuts import get_object_or_404, render_to_response, \
    redirect
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.views.decorators.vary import vary_on_cookie
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.views.generic.list_detail import object_detail
from django.template import RequestContext
from compounddb.models import Compound, Library, LibraryHeader, \
    Annotation, SDFFile, WorkbenchCompounds
from compounddb.models import PropertyField, Property, Plate, \
    Fingerprint
from django.conf import settings
structure_renderer_url = settings.RENDERER_URL
from compounddb.search import search, SearchError, struct_search, \
    async_struct_search, load_async_struct_search_result, \
    AsyncStructSearchNotReady, AsyncStructSearchDoesNotExist
from compounddb import first_mol, InvalidInputError
from django.db.models import Count

from hashlib import md5
from urllib2 import urlopen
from urllib import urlencode
from logging import root, basicConfig
from simplejson import dumps
import re
import openbabel

basicConfig()
try:
    from moleculeformats import smiles_to_sdf, sdf_to_sdf, InputError
except:
    import sys
    sys.path.append('/home/ycao/sdftools')
    from moleculeformats import smiles_to_sdf, sdf_to_sdf, InputError


def h(x):
    return md5(x).hexdigest()


def get_library_by_name(library, flush=False, cache_life=3600 * 24):
    cache_key = h('library:%s' % library)
    if not flush:
        lib = cache.get(cache_key)
    else:
        lib = None
    if lib is None:

        # lib = Library.objects.filter(
        # ....header__name__iexact=library).select_related('header').extra(
        # ....select={'count':
        # ........'''select count(*) from compounddb_compound_library where
        # ........library_id=compounddb_library.id'''}).latest()

        # use django aggregation instead

        lib = \
            Library.objects.filter(header__name__iexact=library).select_related('header'
                ).annotate(count=Count('compound')).latest()
        cache.set(cache_key, lib, cache_life)

    return lib


def all_libraries():
    from compounddb.urls import all_libraries
    cache_key = h('list of libraries')
    if cache.get(cache_key) is not None:
        libraries = cache.get(cache_key)
    else:
        libraries = list(all_libraries.all())  # appending .all to

                            # remove QuerySet-level
                            # cache

        cache.set(cache_key, libraries, 3600 * 24)
    return libraries


def all_library_names():
    cache_key = h('list of library names')
    if cache.get(cache_key) is not None:
        libraries = cache.get(cache_key)
    else:
        libraries = [i.name for i in all_libraries()]
        cache.set(cache_key, libraries, 3600 * 24)
    return libraries


def _id_to_compound(lib, cid):
    """given library name and cid, return compound object"""

    lib = get_library_by_name(lib.strip())
    compound = Compound.objects.get(cid__iexact=cid.strip(),
                                    library=lib)
    return compound


def ajax(request):
    func = request.GET.get('request')
    if not func:

        # default is to list all library names

        return HttpResponse(dumps(all_library_names()),
                            mimetype='text/json')
    elif func == 'id_check':

        # check compound IDs. return object id

        lib = request.GET.get('lib')
        cid = request.GET.get('cid')
        try:
            compound = _id_to_compound(lib, cid)
            iid = compound.id
        except Compound.DoesNotExist, Library.DoesNotExist:
            iid = -1
        return HttpResponse(dumps(dict(id=iid)), mimetype='text/json')
    elif func == 'reverse_id_check':

        # load compound IDs from object id

        iid = request.GET.get('id')
        try:
            compound = Compound.objects.get(id=int(iid))
            lib = compound.library.select_related('header'
                    ).latest().header.name
            response = dict(lib=lib, cid=compound.cid)
        except Compound.DoesNotExist:
            response = dict(lib='', cid='')
        return HttpResponse(dumps(response), mimetype='text/json')


def all_property_fields():
    cache_key = h('list of property fields')
    if cache.get(cache_key) is not None:
        fields = cache.get(cache_key)
    else:
        fields = PropertyField.objects.all().order_by('name')
        cache.set(cache_key, fields, 3600 * 24)
    return fields


def fuzzy_get_library_by_name(library):

    # lib = Library.objects.filter(
    # ....header__name__icontains=library).select_related('header').extra(
    # ........select={'count':
    # ............'''select count(*) from compounddb_compound_library where
    # ............library_id=compounddb_library.id'''}).latest()

    # use django aggregation instead

    lib = \
        Library.objects.filter(header__name__icontains=library).select_related('header'
            ).annotate(count=Count('compound')).latest()

    return lib


def compound_screen(request, compound):
    """load the screens for a specific compound"""

    # load regularly annotated compound

    from screendb.models import Screen, StandardCompoundAnnotation
    import screendb.models
    from screendb.views import get_all_screens
    screen_stat = []
    accessible_screens = dict([(s.id, s) for s in
                              get_all_screens(request)])
    screens = Screen.objects.extra(tables=['screendb_screenfile'],
                                   where=['screendb_screenfile.compound_id=%s'
                                   ,
                                   'screendb_screenfile.screen_id=screendb_screen.id'
                                   ], params=[compound.id]).distinct()
    for s in screens:
        if s.id not in accessible_screens:
            continue
        sca = StandardCompoundAnnotation.objects.filter(screen=s,
                compound=compound)
        if sca.count():
            screen_stat.append((s, 'score: %s' % sca[0].a1_score))
        else:
            screen_stat.append((s, 'no information'))

    # load inactive screens

    for s in compound.inactive_in_screen.all():
        if s.id not in accessible_screens:
            continue
        screen_stat.append((s, 'explictly marked as inactive'))

    # load DTS screen

    dts_set = compound.dtsentry_set.all()
    if dts_set:

        # we check each screen to see 1) whether it has DTS data 2) whether the
        # DTS data of dts_set

        for sid in accessible_screens:
            if hasattr(screendb.models, 'DTS%dEntry' % sid):

                # s is a DTS screen. now test whether any dts data belongs to
                # this screen

                for dts in dts_set:
                    if hasattr(dts, 'dts%dentry' % sid):
                        screen_stat.append((accessible_screens[sid],
                                'DTS data available'))
                        break

    return screen_stat


                       # prevent private compound to be seen

@cache_page(60 * 5)
@vary_on_cookie
def compound_detail(
    request,
    library,
    cid,
    resource,
    ):

    try:
        lib = get_library_by_name(library)
        library = lib.header.name

        # previously select_related was used:
        # .select_related(
        # ....'library', 'sdffile_set', 'fingerprint_set', 'property_set',
        # ....'annotation_set', 'plate_set'
        # ....)
        # but that does not work since select_related only support
        # one-direction ForeignKey and not reverse

        compound = Compound.objects.get(cid__iexact=cid, library=lib)
    except Compound.DoesNotExist, Library.DoesNotExist:
        raise Http404

    # --- inchi/smiles/sdf file

    inchi = compound.inchi
    smiles = compound.smiles

    if resource:
        if resource == 'smiles':
            return HttpResponse(smiles, mimetype='text/plain')
        elif resource == 'inchi':
            return HttpResponse(inchi, mimetype='text/plain')

    sdf = compound.sdffile_set.all()[0].sdffile
    if resource and resource == 'sdf':
        return HttpResponse(sdf, mimetype='text/plain')

    # --- joelib

    excluded_joelibs = ['MW']
    joelib_properties = dict()
    for j in compound.property_set.all():
        if j.field.name == 'MW':

            # joelib weight takes the priority

            compound.weight = j.value
        if j.field.name not in excluded_joelibs:
            short_name = j.field.name
            long_name = j.field.description
            if j.value % 2 == 0:
                joelib_properties[long_name] = (short_name, '%d'
                        % j.value)
            else:
                joelib_properties[long_name] = (short_name, '%.3f'
                        % j.value)

    joelib_properties = joelib_properties.items()
    joelib_properties.sort(key=lambda x: x[1][0])
    if resource and resource == 'property':
        p = '\n'.join(['%-50s %s' % ((_[0])[:50], _[1]) for _ in
                      joelib_properties])
        return HttpResponse(p, mimetype='text/plain')

    if resource:
        raise Http404

    # --- annotation

    excluded_annotations = [
        'name',
        'formula',
        'plate',
        'row',
        'col',
        'smiles',
        'inchi',
        ]
    annotations = dict()
    for a in compound.annotation_set.all():
        if a.name.lower() not in excluded_annotations:
            annotations[a.name] = a.value

    # --- plate

    plates = []
    plate = compound.plate_set.all()
    for p in plate:
        plates.append(dict(format=p.format, plate=p.plate, well=p.well))

    # --- get duplicates via fingerprint

    try:
        fpt = Fingerprint.objects.get(compound=compound)
        dup_fpts = \
            Fingerprint.objects.filter(fingerprint=fpt.fingerprint)
        if len(dup_fpts) == 1:
            dup_fpts = []
    except:
        root.warning('failed to get duplicates for %s' % compound)
        dup_fpts = []

    if 'addWorkbench' in request.POST:
        input_mode = 'view'
        addToWorkbench(compound=compound,
                       username=request.user.username)
        matches = None
        request.user.message_set.create(message='Compound added to workbench'
                )

    return render_to_response('compound.html', dict(
        libname=library,
        compound=compound,
        annotations=annotations,
        annotations_head=annotations.items()[:11],
        annotations_tail=annotations.items()[11:],
        joelib_properties_head=joelib_properties[:11],
        joelib_properties_tail=joelib_properties[11:],
        plates=plates,
        sdf=sdf,
        smiles=smiles,
        inchi=inchi,
        screens=compound_screen(request, compound),
        ), context_instance=RequestContext(request))


def render_image(library, cid):
    cache_key = h('%s/%s/png' % (library, cid))
    if cache.get(cache_key) is not None:
        return cache.get(cache_key)

    # load the sdf to determine the url

    if library == 'manual-sdf':
        sdf = cid
    else:
        lib = get_library_by_name(library)
        sdf = SDFFile.objects.get(compound__library=lib,
                                  compound__cid__iexact=cid).sdffile

        # may throw SDFFile.DoesNotExist

    sdflines = []
    ptn = re.compile(r'^M\s+END')
    for i in sdf.encode('utf-8').splitlines():
        sdflines.append(i)
        if ptn.match(i):
            break
    sdf = '\n'.join(sdflines)
    url = structure_renderer_url + md5(sdf).hexdigest()
    root.info('trying to load from cache the structure of %s:%s'
              % (library, cid))

    # see whether renderer has the image in cache

    try:
        renderer = urlopen(url)
        assert renderer.getcode() != 404
        renderer.close()
    except:

        # not ready. so post the sdf to the renderer

        renderer = urlopen(structure_renderer_url,
                           urlencode(dict(sdf=sdf)))
        url = renderer.geturl()
    renderer.close()

    cache.set(cache_key, url, 3600 * 24)

    return url


# the following function was about to be deprecated for speed concern, however
# for support of personal library when SDF cannot be accessed from the
# renderer directly from HTTP, this can offer value

def compound_image(request, library, cid):
    url = render_image(library, cid)
    return redirect(url)


@cache_page(3600 * 24)
@vary_on_cookie
def library_content(request, library, page=1):
    if page is None:
        page = 1
    try:
        page = int(page)
    except ValueError:
        raise Http404
    try:
        lib = get_library_by_name(library)
        compounds = Compound.objects.filter(library=lib)
    except Library.DoesNotExist:
        raise Http404
    compounds.count = lambda : lib.count
    compounds_page = Paginator(compounds, 10).page(int(page))
    return render_to_response('library.html', dict(libname=library,
                              compounds_page=compounds_page),
                              context_instance=RequestContext(request))


@cache_page(60)
@vary_on_cookie
def annotation_search(request):
    pure_query = query = request.GET.get('query', '')
    page = int(request.GET.get('p', '1'))
    matches = []
    if query:
        try:
            (pure_query, matches) = search(query, page, request)
        except SearchError, e:
            return render_to_response('search.html', dict(error=e,
                    query=query),
                    context_instance=RequestContext(request))

    return render_to_response('search.html', dict(
        p=page,
        query=query,
        pure_query=pure_query,
        matches=matches,
        libraries=all_libraries(),
        fields=[(i.name.replace(' ', '__'), i.description) for i in
                all_property_fields()],
        ), context_instance=RequestContext(request))


def structure_search(request):
    """
....structure search. the following query SDF processing is copied from ei
...."""

    libraries = all_libraries()
    if request.method == 'GET':
        hash = request.GET.get('ref')
        wait = request.GET.get('wait')
        ajax = request.GET.get('ajax')
        smiles = request.GET.get('smiles')
        if ajax:
            try:
                load_async_struct_search_result(ajax)
            except AsyncStructSearchNotReady:
                return HttpResponse('{"status":"wait"}',
                                    mimetype='text/plain')
            except:
                return HttpResponse('{"status":"error"}',
                                    mimetype='text/plain')
            return HttpResponse('{"status":"ok"}', mimetype='text/plain'
                                )
        elif hash:
            try:
                (compounds, info) = \
                    load_async_struct_search_result(hash)
            except AsyncStructSearchNotReady:
                return HttpResponseRedirect(request.path + '?wait='
                        + hash)
            except AsyncStructSearchDoesNotExist:
                request.user.message_set.create(message='No such search'
                        )
                return HttpResponseRedirect(request.path)
            info['compounds'] = compounds
            info['fields'] = [(i.name.replace(' ', '__'),
                              i.description) for i in
                              all_property_fields()]
            return render_to_response('structure_search.html', info,
                    context_instance=RequestContext(request))
        elif wait:
            info = cache.get(h('async search:' + wait))
            if not info:

                # ignore cache lost

                info = dict()
            info['hash'] = wait
            return render_to_response('structure_search_wait.html',
                    info, context_instance=RequestContext(request))
        else:

            # show empty query form

            return render_to_response('structure_search.html',
                    dict(libraries=libraries,
                    post_data=dict(smiles=smiles)),
                    context_instance=RequestContext(request))
    else:
        input_mode = ''
        selected_libs = request.POST.getlist('library')
        libs = []
        for lib in selected_libs:
            libs.append(get_library_by_name(lib))
        for lib in libraries:
            if lib.name in selected_libs:
                lib.selected = True
            else:
                lib.selected = False
        sdf = None
        if not libs:
            request.user.message_set.create(message='No library selected. You must select at least one library.'
                    )
        elif 'smiles' in request.POST:
            input_mode = 'smiles-input'
            try:
                sdf = smiles_to_sdf(str(request.POST['smiles']))
            except InputError:
                request.user.message_set.create(message='Invalid SMILES string!'
                        )
                sdf = None
        elif 'sdf' in request.FILES:
            input_mode = 'sdf-upload'
            try:
                sdf = first_mol(request.FILES['sdf'])
                sdf = sdf_to_sdf(sdf)
            except (InputError, InvalidInputError):
                request.user.message_set.create(message='Invalid SDF!')
                sdf = None
        elif 'sdf' in request.POST:
            if 'draw' in request.POST:
                input_mode = 'draw'
            else:
                input_mode = 'sdf-input'
            sdf = request.POST['sdf']
            try:
                sdf = first_mol(request.POST['sdf'])
                sdf = sdf_to_sdf(sdf)
            except (InputError, InvalidInputError):
                request.user.message_set.create(message='Invalid SDF!')
                sdf = None

        if not sdf:
            return render_to_response('structure_search.html',
                    dict(input_mode=input_mode,
                    selected_libs=selected_libs,
                    post_data=request.POST, libraries=libraries),
                    context_instance=RequestContext(request))
        else:
            query_rendered = render_image('manual-sdf', sdf)
            hash = query_rendered.strip('/')
            hash = hash.rsplit('/', 1)[1]

            # compounds = struct_search(sdf, libs)

            search_term = dict(query_url=query_rendered,
                               input_mode=input_mode,
                               selected_libs=selected_libs,
                               post_data=request.POST,
                               libraries=libraries)
            async_struct_search(hash, sdf, libs, search_term)
            cache.set(h('async search:' + hash), search_term, 60)
            return HttpResponseRedirect(request.path + '?wait=' + hash)


def addToWorkbench(compound, username):
    compound = WorkbenchCompounds(compound=compound, username=username)
    compound.save()


