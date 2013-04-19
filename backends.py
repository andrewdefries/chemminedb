#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.contrib.auth.models import User, Group
from django.forms.fields import email_re
from django.contrib.auth.backends import ModelBackend
from datetime import datetime, timedelta
from django.conf import settings


class EmailBackend(ModelBackend):

    def authenticate(self, username=None, password=None):

        # handle "guest" login

        if username == 'guest':

            # clean the old guest account

            guests = Group.objects.get(name='guests')
            deadline = datetime.now() - timedelta(weeks=4)
            guests.user_set.filter(last_login__lt=deadline).delete()
            name = 'guest_%s' % datetime.now()
            name = name[:30]
            user = User.objects.create_user(username=name, email='')
            guests.user_set.add(user)
            user.save()
            return user

        # If username is an email address, then try to pull it up

        if email_re.search(username):
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None
        else:

            # We have a non-email address username we should try username
            # We only allow staffs to do this

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
            if not user.is_staff:
                return None
        if user.check_password(password):
            return user


