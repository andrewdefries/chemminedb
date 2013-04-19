#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns(  # Example:
                         # (r'^cmngtest/', include('cmngtest.foo.urls')),
                         # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
                         # to INSTALLED_APPS to enable admin documentation:
                         # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
                         # Uncomment the next line to enable the admin:
                         # (r'^admin/(.*)', admin.site.root),
                         # (r'^static/(?P<path>.*)', 'django.views.static.serve',
                         # ....{'document_root': root + '/static/'}),
                         # dts tabular view
                         # dts virtual plate
    '',
    url(r'^$', 'screendb.views.list_all_screens', name='all-screens'),
    url(r'^(?P<screen_id>\d+)/delete_screen/',
        'screendb.views.delete_screen', name='delete-screen'),
    url(r'^(?P<screen_id>\d+)/$', 'screendb.views.screen_detail',
        name='screen-detail'),
    url(r'^(?P<screen_id>\d+)/add/$', 'screendb.views.add_file',
        name='add-file-test'),
    url(r'^file/(?P<file_id>\d+)/(?P<typehint>\w*)',
        'screendb.views.serve_file', name='serve-file'),
    url(r'^file/(?P<file_id>\d+)/', 'screendb.views.serve_file',
        name='serve-file'),
    url(r'^dts/(?P<screen_id>\d+)/$', 'screendb.views.dts',
        name='dts-data'),
    url(r'^dts/(?P<screen_id>\d+)/vp/$', 'screendb.views.virtualplate',
        name='virtual-plate'),
    )
