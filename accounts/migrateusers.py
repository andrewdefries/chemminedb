#!/usr/bin/python
# -*- coding: utf-8 -*-


def import_user():
    from hashlib import md5
    from django.contrib.auth.models import User
    from accounts.models import UserProfile
    from datetime import datetime
    f = file('migrate_users.csv')
    for line in f:

        (
            _,
            last,
            first,
            hash,
            email,
            inst,
            reg,
            _,
            ) = [i.replace('"', '').strip() for i in line.split('|')]
        user = \
            User.objects.get_or_create(username=md5(str(email)).hexdigest()[:30])[0]
        user.password = ''
        user.email = email
        user.last_name = last
        user.first_name = first
        user.save()
        profile = UserProfile.objects.get_or_create(user=user)[0]
        profile.institute = inst
        profile.save()
        user.password = 'sha1$$' + hash
        try:
            user.date_joined = datetime.strptime(reg,
                    '%m/%d/%y %I:%M %p')
        except:
            pass
        user.save()


