#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.contrib.auth.models import User, Group
from django.contrib.auth import login, authenticate
from django.conf import settings
if settings.USE_CMS:
    from cms.views import get_page_context
    from cms.models import Page
    from cms.cms_global_settings import SITE_TITLE


def cm_context(request):
    """ 
.... A context processor to load page context from CMS application, if
.... settings.USE_CMS is set
.... It also assigns random user object to anonymous users
...."""

    context_extra = dict()
    if request.META['PATH_INFO'] == '/admin/':
        return context_extra

    # anonymous user are automatically signed in using its session id

    if not request.user.is_authenticated():

        # user is not authenticated and therefore is anonymous. let's check
        # a session variable to see whether cookie is ON

        if request.session.get('is_anonymous', False):

            # set previously and success, meaning cookie is on

            user = authenticate(username='guest')
            login(request, user)
        else:

            # either cookie is not ON or we have not set the session
            # variable yet. Let's try set it. Useful to test cookie

            request.session['is_anonymous'] = True

    # we set the context variable to be used in templates

    context_extra['user_is_anonymous'] = \
        not request.user.is_authenticated() or not request.user.email
    if settings.USE_CMS:
        if request.path.endswith('/'):
            url = request.path[1:-1]
        else:
            url = request.path[1:]
        language = 'en'
        while True:
            pages = Page.objects.filter(override_url=True,
                    overridden_url=url, redirect_to__isnull=True)
            if pages.count():
                break
            if url.endswith('*'):
                url = url[:-1]
                continue
            url = '/'.join(url.split('/')[:-1])
            if not url:
                break
            else:
                url += '*'
        if pages:
            page = pages[0]

            # cannot call get_page_context here, coz get_page_context
            # will create a RequestContext, which in turns calls this
            # context processor, results in a call loop

            context_extra.update(dict(
                page=page,
                path=list(page.get_path()),
                url=request.path,
                language=language,
                root='',
                title=page.title,
                site_title=SITE_TITLE,
                RENDERER_URL=settings.RENDERER_URL,
                ))
    return context_extra


