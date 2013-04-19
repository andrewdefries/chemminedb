#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from cmplatform.views import limit_to_user, app, app_init, app_read, \
    app_write, app_exit, running_app, add_user_object, list_running_apps
from django.views.generic.list_detail import object_detail, object_list
from cmplatform import models
from django.conf import settings

# see whether TESTING is set to True in settings

try:
    show_testing = settings.TESTING
except:
    show_testing = False
if settings.DEBUG or show_testing:
    all_apps = \
        models.Application.objects.filter(app_type__in=[models.Application.REGULAR,
            models.Application.TESTING, models.Application.VIEWER])
else:
    all_apps = \
        models.Application.objects.filter(app_type__in=[models.Application.REGULAR])

all_running_apps = \
    models.RunningApplication.objects.all().order_by('-start_time')

urlpatterns = patterns(  # show the start page
                         # get shortened list
                         # list of all applications
                         # show one application
                         # list of all running applications of a user
                         # show one application
                         # user object
                         # for application to communicate with platform
    '',
    url(r'^$', 'cmplatform.views.startpage', name='app_startpage'),
    url(r'^shortlist$', 'cmplatform.views.shortlist'),
    url(r'^all/$', object_list, dict(queryset=all_apps), name='all_apps'
        ),
    url(r'^(?P<object_id>\d+)/$', app, dict(queryset=all_apps),
        name='app_details'),
    url(r'^running/$', list_running_apps,
        dict(queryset=all_running_apps,
        template_name='runningapplication_list.html'),
        name='all_running_apps'),
    url(r'^running/(?P<object_id>\d+)/$', running_app,
        dict(queryset=all_running_apps), name='running_app_details'),
    url(r'obj/$', add_user_object, dict(), name='add_user_object'),
    (r'^_init/(?P<app_id>\d+)/(?P<token>[^/]+)/$', app_init),
    (r'^_read/(?P<app_id>\d+)/(?P<token>[^/]+)/$', app_read),
    (r'^_write/(?P<app_id>\d+)/(?P<token>[^/]+)/$', app_write),
    (r'^_exit/(?P<app_id>\d+)/(?P<token>[^/]+)/$', app_exit),
    )
