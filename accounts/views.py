#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.views import logout, password_change
from django.contrib.auth.models import User
from accounts.forms import SignUpForm
from django.conf import settings
from accounts.models import UserProfile
import django.dispatch
login_done = django.dispatch.Signal(['request'])

# the following login is copied from auth.views. just modify to make it
# return the context instead of response
# also, add argument 'force_get' to force GET response
# 'force_get' is used because we put both login and signup forms in the
# same page and route them to the same cm_login function

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import Site, RequestSite


def login(
    request,
    template_name='registration/login.html',
    redirect_field_name=REDIRECT_FIELD_NAME,
    force_get=False,
    ):
    '''Displays the login form and handles the login action.'''

    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if not force_get and request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():

            # Light security check -- make sure redirect_to isn't garbage.

            if not redirect_to or '//' in redirect_to or ' ' \
                in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, form.get_user())
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        form = AuthenticationForm(request)
    request.session.set_test_cookie()
    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)
    return {'form': form, redirect_field_name: redirect_to,
            'site_name': current_site.name}


@never_cache
def cm_login(request, *args, **kargs):
    old_user = request.user  # for identifying anonymous -> logged in
    resp = dict()

    # handle the registration form

    form_signup = SignUpForm()
    resp['form_signup'] = form_signup
    if request.method == 'POST' and request.POST.get('newaccount'):
        rg_resp = cm_useradd(request, *args, **kargs)
        if isinstance(rg_resp, HttpResponseRedirect):
            return rg_resp
        else:
            resp.update(rg_resp)
        login_resp = login(request, force_get=True,
                           redirect_field_name='l', *args, **kargs)
    else:
        login_resp = login(request, redirect_field_name='l', *args,
                           **kargs)

    # signal the login event

    if old_user.id != request.user.id:
        request.session['is_anonymous'] = False
        login_done.send(sender=None, request=request)

    if isinstance(login_resp, HttpResponseRedirect):
        return login_resp
    else:
        resp.update(login_resp)

    return render_to_response(kargs.get('template_name',
                              'registration/login.html'), resp,
                              context_instance=RequestContext(request))


@never_cache
def cm_logout(request, *args, **kargs):
    return logout(request, redirect_field_name='l', *args, **kargs)


def cm_useradd(request, *args, **kargs):
    """create a new user"""

    from hashlib import md5
    form = SignUpForm(request.POST)
    if form.is_valid():
        user = \
            User.objects.create_user(username=md5(str(form.cleaned_data['email'
                ])).hexdigest()[:30],
                password=form.cleaned_data['password'],
                email=form.cleaned_data['email'])
        user.last_name = form.cleaned_data['last']
        user.first_name = form.cleaned_data['first']
        user.save()
        profile = UserProfile(user=user,
                              institute=form.cleaned_data['institute'])
        profile.save()
        request.user.message_set.create(message='Your account has been created. Please log in.'
                )
        return HttpResponseRedirect(request.get_full_path())
    else:
        return dict(form_signup=form)


