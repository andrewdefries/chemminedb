#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from cms.views import handler as _handler
from cms.views import search
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie


@cache_page(60 * 5)
@vary_on_cookie
def handler(*args, **kwargs):
    return _handler(*args, **kwargs)

urlpatterns = patterns('', url(r'^search/', search, name='cms_search'),
                       url(r'^.*/$', handler), url(r'^$', handler,
                       name='cms_root'))
