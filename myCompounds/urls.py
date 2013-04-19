#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from views import uploadCompound

urlpatterns = patterns(r'', (r'^jscripts/', r'django.views.static.serve'
                       , {'document_root': 'jscripts'}), url(r'',
                       uploadCompound))
