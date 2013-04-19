#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from cmplatform import models
import uuid
from urllib2 import urlopen
import logging


class ApplicationNotFoundError(Exception):

    def __str__(self):
        return 'Application Cannot Be Found'


class ApplicationCannotBeStartedError(Exception):

    def __init__(self, info):
        self.info = info

    def __str__(self):
        return 'Application Cannot Be Started: %s' % self.info


class RunningApplicationNotFoundError(Exception):

    def __str__(self):
        return 'Running Application Cannot Be Found'


class RunningApplicationStatusError(Exception):

    def __str__(self):
        return 'Running Application Status Transition Error'


class TokenMismatchError(Exception):

    def __str__(self):
        return 'Running Application Token Mismatch'


def invoke_app(user, app_id, input):
    """invoke an application"""

    app = models.Application.objects.filter(pk=app_id)
    if app.count() != 1:
        raise ApplicationNotFoundError
    app = app.get()
    r = models.RunningApplication(user=user, application=app,
                                  token=str(uuid.uuid4()), stdin=input)
    r.save()
    logging.info('new RunningApplication instance created with id=%s'
                 % r.id)

    # invoking remote application

    try:
        _ = ('' if '?' in app.invoking_url else '?')
        x = urlopen(app.invoking_url + _
                    + 'chemmine_id=%s&chemmine_token=%s' % (r.id,
                    r.token))
    except:
        update_status(r, models.RunningApplication.FAILED)
        ex = sys.exc_info()[1]
        raise ApplicationCannotBeStartedError(ex)
    update_status(r, models.RunningApplication.INVOKED)
    logging.info('RunningApplication instance %s status set to invoked'
                 % r.id)
    x.read()
    return r


def find_runing_app(
    r_app_id,
    token,
    mask_died=True,
    silent=False,
    ):

    r_app = models.RunningApplication.objects.filter(pk=r_app_id)
    if r_app.count() != 1:
        if silent:
            return None
        else:
            raise RunningApplicationNotFoundError
    r_app = r_app.get()
    if r_app.token != token:
        if silent:
            return None
        else:
            raise TokenMismatchError
    if r_app.status in models.RunningApplication.died_status \
        and mask_died:
        logging.info('Finished/Failed RunningApplication instance %s masked'
                      % r_app.id)
        if silent:
            return None
        else:
            raise RunningApplicationNotFoundError
    return r_app


def update_status(r_app, status, silent=True):
    if status == r_app.status:
        logging.info('RunningApplication instance %s status unchanged'
                     % r_app.id)
    elif r_app.status in models.RunningApplication.died_status:
        logging.error('Finished/Failed RunningApplication instance %s cannot change status'
                       % r_app.id)
        if not silent:
            raise RunningApplicationStatusError
    elif r_app.status > status:
        logging.error('RunningApplication instance %s tries to reverse status'
                       % r_app.id)
        if not silent:
            raise RunningApplicationStatusError
    else:
        old_status = r_app.status
        r_app.status = status
        logging.info('RunningApplication instance %s status updated from %s to %s'
                      % (r_app.id, old_status, status))
        r_app.save()


def read_running_app_input(r_app_id, token):
    """Read input data for a running app"""

    r_app = find_runing_app(r_app_id, token)
    update_status(r_app, models.RunningApplication.RUNNING)
    logging.info('RunningApplication instance %s read %s chars'
                 % (r_app.id, len(r_app.stdin)))
    return r_app.stdin


def write_running_app_output(r_app_id, token, output):
    """Write output data for a running app"""

    r_app = find_runing_app(r_app_id, token)
    update_status(r_app, models.RunningApplication.RUNNING)
    r_app.stdout = output
    r_app.save()
    logging.info('RunningApplication instance %s writes %s chars'
                 % (r_app.id, len(output)))


