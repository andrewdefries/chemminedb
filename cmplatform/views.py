#!/usr/bin/python
# -*- coding: utf-8 -*-

from cmplatform import models, forms, invoke_app, \
    read_running_app_input, write_running_app_output, find_runing_app, \
    update_status
from cmplatform import ApplicationNotFoundError, \
    RunningApplicationStatusError, TokenMismatchError, \
    RunningApplicationStatusError, RunningApplicationNotFoundError, \
    ApplicationCannotBeStartedError

from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.views.generic.list_detail import object_detail, object_list
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.template import RequestContext
import logging
import datetime
from simplejson import dumps
from compounddb.models import WorkbenchCompounds
from compounddb.search import search

try:
    from moleculeformats import batch_sdf_to_smiles, \
        batch_smiles_to_smiles
except:
    import sys
    sys.path.append('/home/ycao/sdftools')
    from moleculeformats import batch_sdf_to_smiles, \
        batch_smiles_to_smiles


def startapp(request, app_id, input):
    try:
        r = invoke_app(request.user, int(app_id), input)
        return HttpResponseRedirect(r.get_absolute_url())
    except ValueError:
        raise Http404
    except ApplicationNotFoundError:
        logging.error('invoking nonexist application: %s' % app_id)
        request.user.message_set.create(message='Error:No such application: #%s'
                 % app_id)
        return HttpResponseRedirect(request.get_full_path())
    except ApplicationCannotBeStartedError:
        logging.error('cannot invoke application: %s' % app_id)
        request.user.message_set.create(message='Error:Application cannot be started'
                )
        return HttpResponseRedirect(request.get_full_path())


def do_add_user_object(
    request,
    data,
    name,
    type=None,
    source=None,
    source_class=None,
    ):

    # if type is not given, try parse as JSON. fall back to pure text

    if type is None:
        try:
            json_obj = models.JSONData(data, type='json')
        except:
            json_obj = models.JSONData(data, type='text')
    json_obj = models.JSONData(data, type=type)
    json_obj.name = name
    json_obj.source = source
    json_obj.source_class = source_class

    # serialize only for registered users (not guests)

    if request.user.email:
        json_obj.serialize(request.user)
    if 'user_objects' not in request.session:
        request.session['user_objects'] = dict()
    request.session['user_objects'][name] = json_obj
    request.session.modified = True
    return


def getWorkbenchCompounds(request):
    page = int(request.GET.get('p', '1'))
    matches = []
    (pure_query, matches) = search('library: myCompounds', page,
                                   request)
    if len(matches[0][1]) == 0:
        matches = None
    return (page, matches)


def startpage(request):
    """show the Start page, that provides a general conceptual overview and
....also a launchpad"""

    (page, matches) = getWorkbenchCompounds(request)
    if request.method == 'GET':
        objs = request.session.get('user_objects', dict()).values()
        apps = \
            models.Application.objects.filter(app_type__in=[models.Application.REGULAR]).filter(input_type='text/smiles'
                )

        # userCompounds = WorkbenchCompounds.objects.filter(username=request.user.username)
        # matches = []
        # for compound in userCompounds:
            # matches.append(compound.compound)
            # matches = [matches]

        return render_to_response('startpage.html',
                                  dict(user_objects=objs, apps=apps,
                                  p=1, matches=matches),
                                  context_instance=RequestContext(request))
    else:
        ajax = 'ajax' in request.POST
        error = None

        if 'emptyWorkbench' in request.POST:
            input_mode = 'view'
            emptyWorkbench(request.user.username)
            matches = None
            error = 'Workbench emptied!'
            ajax = None

        # on POST, check input compound and start the requested app

        if 'upload-format' not in request.POST:
            error = \
                'Error: Invalid form submission. Did you have JavaScript enabled?'

        # read the input if there is no error

        if not error:

            format = request.POST['upload-format']
            try:
                input = ''
                if format == 'workspace':
                    userCompounds = \
                        WorkbenchCompounds.objects.filter(username=request.user.username)
                    for compound in userCompounds:
                        input += compound.compound.smiles + '\n'
                elif format == 'smiles-input':
                    (input, n_err) = \
                        batch_smiles_to_smiles(request.POST['smiles'])
                elif format == 'sdf-input':
                    (input, n_err) = \
                        batch_sdf_to_smiles(request.POST['sdftext'])
                elif format == 'sdf-upload':
                    (input, n_err) = \
                        batch_sdf_to_smiles(request.FILES['sdf'].read())

                if not input:
                    raise Exception
            except:
                error = \
                    'Error: We cannot process your upload. It might be empty or invalid.'

        # start the app if there is no error

        if not error:
            if 'app2' not in request.POST or not request.POST['app2']:
                error = 'Error: You did not specify a tool to start.'
            else:
                try:
                    r = startapp(request, request.POST['app2'], input)

                    # if no error, save the user's upload

                    do_add_user_object(request, input, 'last upload',
                            type='text/smiles')
                except:
                    if not ajax:
                        raise
                assert isinstance(r, HttpResponseRedirect)

        # now direct user to the right place

        if not ajax:
            if error:
                request.user.message_set.create(message=error)
                return HttpResponseRedirect(request.get_full_path())
            return r
        else:
            if error:
                response = dict(error=error)
            else:
                response = dict(redirect=r['Location'])
                if n_err:
                    response['info'] = \
                        'Warning: %d compounds cannot be processed' \
                        % n_err
            return HttpResponse(dumps(response), mimetype='text/json')


def shortlist(request):
    if request.is_ajax():
        appnames = []
        currentApp = request.GET['currentApp']

        # get current app output format

        output_type = \
            models.Application.objects.filter(app_type__in=[models.Application.REGULAR]).filter(name=currentApp)[0].output_type

        # get list of apps matching that format

        apps = \
            models.Application.objects.filter(app_type__in=[models.Application.REGULAR]).filter(input_type=output_type)
        for app in apps:
            appnames.append(app.name)
        response = dict(shortlist=appnames)
    else:
        response = dict(shortlist='ERROR')
    return HttpResponse(dumps(response), 'text/json')


def app(
    request,
    object_id,
    queryset,
    *args,
    **kargs
    ):
    """upon GET request, show the application; upon POST, invoke it"""

    a = queryset.get(pk=int(object_id))
    if not a:
        raise Http404
    if request.method == 'GET':
        objs = request.session.get('user_objects', dict()).values()
        return render_to_response('application_detail.html',
                                  dict(object=a, user_objects=objs),
                                  context_instance=RequestContext(request))
    else:

        # upon POST, invoke application

        if request.POST.get('object_name') and request.POST.get('input'
                ):
            logging.warning('Got both object and input when invoking')

        # first, try reading object

        obj_names = request.POST.get('object_name')
        if obj_names:
            input = []
            for obj_name in obj_names.split('|'):
                if obj_name not in request.session['user_objects']:
                    logging.error('Could not find object:' + obj_name)
                    request.user.message_set.create(message="Error:No object with name '%s' could be found"
                             % obj_name)
                    return HttpResponseRedirect(request.get_full_path())
                input.append(str(request.session['user_objects'
                             ][obj_name]))
            logging.info('input: %d objects' % len(input))
            input = a.input_separator.join(input)
            logging.info('input flatted to be' + input)
        else:
            input = request.POST.get('input', '')
        return startapp(request, object_id, input)


def limit_to_user(f):
    """
....A decorator for views that modifies the queryset by appending
....user=request.user
...."""

    def decorated(
        request,
        queryset,
        *args,
        **kargs
        ):

        queryset = queryset.filter(user=request.user)
        return f(request, queryset=queryset, *args, **kargs)

    return login_required(decorated)


def handle_error(f):
    """A decorator to send errors to applications"""

    def decorated(*args, **kargs):
        try:
            return f(*args, **kargs)
        except (ApplicationNotFoundError,
                RunningApplicationNotFoundError,
                RunningApplicationStatusError, TokenMismatchError,
                RunningApplicationStatusError), e:

            return HttpResponse('ERROR: %s' % e,
                                content_type='text/plain')

    return decorated


# The following views are for communications with applications

@handle_error
def app_init(request, app_id, token):
    """applications calls init"""

    r = find_runing_app(int(app_id), token)
    update_status(r, models.RunningApplication.RUNNING)
    return HttpResponse('''OK

''', content_type='text/plain')


@handle_error
def app_read(request, app_id, token):
    """application reads data"""

    return HttpResponse('''OK

'''
                        + read_running_app_input(int(app_id), token),
                        content_type='text/json')


@handle_error
def app_write(request, app_id, token):
    """application writes data"""

    if request.method == 'POST':
        output = request.POST.get('output', '')
        write_running_app_output(int(app_id), token, output)
        return HttpResponse('''OK

''', content_type='text/plain')
    else:
        return render_to_response('app_write.html', dict(app_id=app_id))


@handle_error
def app_exit(request, app_id, token):
    """applications calls init"""

    r = find_runing_app(int(app_id), token)
    r.stop_time = datetime.datetime.now()
    update_status(r, models.RunningApplication.FINISHED)
    return HttpResponse('''OK

''', content_type='text/plain')


@limit_to_user
def running_app(
    request,
    object_id,
    queryset,
    *args,
    **kargs
    ):
    """upon GET request, show the running application or check status;
....upon POST, pipe to another application or save output"""

    r_app = queryset.get(pk=int(object_id))
    if not r_app:
        raise Http404
    if len(r_app.stdin) > 80:
        r_app.stdin_truncated = r_app.stdin[:80]
    if len(r_app.stdout) > 80:
        r_app.stdout_truncated = r_app.stdout[:80]
    if request.method == 'GET':

        # ajax request?

        if 'ajax' in request.GET and request.GET['ajax']:
            if request.GET['ajax'] == 'status':
                return HttpResponse('{"status":"%s"}'
                                    % r_app.get_status_display(),
                                    mimetype='text/json')
        error = r_app.stdout.upper().startswith('ERROR')

        # for viewer, redirect automatically on completion

        redirect = ''
        if not error and r_app.status \
            == models.RunningApplication.FINISHED \
            and r_app.application.app_type == models.Application.VIEWER:

            # silent redirect only for chemmine-hosted apps

            if r_app.stdout.startswith('http://chemmine.ucr.edu') \
                or r_app.stdout.startswith('/'):
                return HttpResponseRedirect(r_app.stdout)
            else:
                redirect = r_app.stdout

        # otherwise, show the details for the app

        (saved, viewers, processors) = (None, [], [])
        if r_app.status == models.RunningApplication.FINISHED:
            saved = None

            # check whether the result has been saved

            if 'user_objects' in request.session:
                for name in request.session['user_objects']:
                    if request.session['user_objects'][name].source \
                        and request.session['user_objects'
                            ][name].source == r_app:
                        saved = name

            # compatible next-steps; show nothing if error

            if error:
                _ = []
            else:
                _ = \
                    models.Application.objects.filter(input_type=r_app.application.output_type)
                _ = list(_)
            viewers = [i for i in _ if i.app_type
                       == models.Application.VIEWER]
            processors = [i for i in _ if i.app_type
                          == models.Application.REGULAR]
        return render_to_response('runningapplication_detail.html',
                                  dict(
            object=r_app,
            saved=saved,
            error=error,
            running=r_app.status in [models.RunningApplication.RUNNING,
                    models.RunningApplication.INVOKED],
            viewers=viewers,
            redirect=redirect,
            processors=processors,
            can_process=viewers or processors,
            ), context_instance=RequestContext(request))
    else:

        # upon POST, it could be a pipe request or to save the output

        if 'processor' in request.POST and request.POST['processor']:
            return startapp(request, request.POST['processor'],
                            r_app.stdout)
        else:
            uo_name = request.POST.get('name')
            if '|' in uo_name:
                request.user.message_set.create(message="Error:'|' is not allowed in object names"
                        )
                return HttpResponseRedirect(request.get_full_path())
            if not uo_name:
                request.user.message_set.create(message='Error:object name cannot be empty'
                        )
                return HttpResponseRedirect(request.get_full_path())
            do_add_user_object(
                request,
                r_app.stdout,
                uo_name,
                source=r_app,
                source_class=r_app.application,
                type=r_app.application.output_type,
                )
            return HttpResponseRedirect(request.get_full_path())


@limit_to_user
def list_running_apps(
    request,
    queryset,
    *args,
    **kargs
    ):
    """upon GET request, show all running applications;
....upon POST, process deletion"""

    if request.method == 'GET':
        return object_list(request, queryset=queryset, *args, **kargs)
    else:
        ra_ids = []
        for ra_id in request.POST:
            if ra_id.startswith('ra_'):
                try:
                    ra_id = int(ra_id[len('ra_'):])
                    ra_ids.append(ra_id)
                except:
                    continue
        logging.info('Delete following running app:%s' % ra_ids)
        if ra_ids:
            queryset.filter(pk__in=ra_ids).delete()
            request.user.message_set.create(message='%d %s deleted'
                    % (len(ra_ids), len(ra_ids) > 1 and 'applications'
                    or 'application'))
        else:
            request.user.message_set.create(message='No application have been deleted'
                    )
        return HttpResponseRedirect(request.get_full_path())


def add_user_object(request, *args, **kargs):
    """add a new user object"""

    # on GET, show the form

    if request.method == 'GET':
        return render_to_response('user_object.html',
                                  dict(form=forms.UserObjectForm()),
                                  context_instance=RequestContext(request))
    else:

    # on POST, process the input

        form = forms.UserObjectForm(request.POST)

        # with valid form, save the result to both session and db

        if form.is_valid():
            uo_name = form.cleaned_data['name']

            # check name

            if not form.cleaned_data['override'] and uo_name \
                in request.session.get('user_objects', dict()):
                error = 'Name conflict, and you chose not to override'
                return render_to_response('user_object.html',
                        dict(form=form, error=error),
                        context_instance=RequestContext(request))

            # check explicit type, and instance JSON object accordingly

            type = None
            if form.cleaned_data['pure_text']:
                type = 'text/plain'
            do_add_user_object(request, form.cleaned_data['content'],
                               uo_name, type=type)

            # let the user konw

            request.user.message_set.create(message='New object has been created'
                    )
            return HttpResponseRedirect(request.get_full_path())
        else:

        # with invalid form, show it

            return render_to_response('user_object.html',
                    dict(form=form),
                    context_instance=RequestContext(request))


def load_user_object(sender, request, **kargs):
    """
....load user object from database; this is a callback for login signal
...."""

    logging.info('logged in as %s' % request.user)
    uo = models.UserObject.objects.filter(owner=request.user)
    for i in uo:
        json_obj = models.JSONData(i.value, name=i.name, type=i.type)
        json_obj.source = i.source
        json_obj.source_class = i.source_class

        # save to session

        if 'user_objects' not in request.session:
            request.session['user_objects'] = dict()
        request.session['user_objects'][i.name] = json_obj
        request.session.modified = True


# must use chemmineng.accounts.views and not accounts.views because the later
# will instance another login_done, while signal will be sent through
# another channel

from chemmineng.accounts.views import login_done
login_done.connect(load_user_object)


def emptyWorkbench(username=None):
    if username:
        WorkbenchCompounds.objects.filter(username=username).delete()


