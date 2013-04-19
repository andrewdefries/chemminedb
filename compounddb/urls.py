#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from django.conf.urls.defaults import *
from django.views.generic.list_detail import object_list as _object_list
from django.views.decorators.vary import vary_on_cookie
from compounddb.models import LibraryHeader
from django.views.decorators.cache import cache_page

# Uncomment the next two lines to enable the admin:

from django.contrib import admin
admin.autodiscover()

root = os.path.dirname(__file__)


@cache_page(60 * 60)
@vary_on_cookie
def object_list(*args, **kwargs):
    return _object_list(*args, **kwargs)

all_libraries = \
    LibraryHeader.objects.extra(select={'count': 'select count(*) from compounddb_compound_library where library_id=(select compounddb_library.id from compounddb_library where compounddb_library.header_id = compounddb_libraryheader.id order by compounddb_library.created_time desc limit 1)'
                                })

urlpatterns = patterns(  # Example:
                         # (r'^cmngtest/', include('cmngtest.foo.urls')),
                         # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
                         # to INSTALLED_APPS to enable admin documentation:
                         # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
                         # Uncomment the next line to enable the admin:
                         # (r'^admin/(.*)', admin.site.root),
                         # (r'^static/(?P<path>.*)', 'django.views.static.serve',
                         # ....{'document_root': root + '/static/'}),
    '',
    url(r'^annotation/$', 'compounddb.views.annotation_search',
        name='annotation-search'),
    url(r'^structure/$', 'compounddb.views.structure_search',
        name='structure-search'),
    url(r'^(?P<library>[,a-zA-Z0-9 _-]+)/(:(?P<page>[0-9]+))?$',
        'compounddb.views.library_content', name='library_content'),
    url(r'^(?P<library>[,a-zA-Z0-9 _-]+)/(?P<cid>[a-zA-Z0-9 _-]+)/png',
        'compounddb.views.compound_image', name='compound_image'),
    url(r'^(?P<library>[,a-zA-Z0-9 _-]+)/(?P<cid>[a-zA-Z0-9 _-]+)/(?P<resource>\w*)$'
        , 'compounddb.views.compound_detail', name='compound_detail'),
    url(r'^$', object_list, dict(queryset=all_libraries),
        name='compound_libraries'),
    url(r'^_ajax$', 'compounddb.views.ajax', name='ajax'),
    )
