# Create your views here.
from django.http import Http404, HttpResponse, HttpResponseRedirect, \
	HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.views.generic.list_detail import object_detail
from django.contrib import auth
from screendb.models import *
import screendb.models
from logging import root, basicConfig
from time import time
from simplejson import dumps
from django.template import Template, Context
from django.template.loader import get_template
from django.utils.html import escape, strip_tags
from django.core.cache import cache
from django.core.paginator import Paginator
from re import compile

basicConfig()

def perm(user, screen, action):

	if user.is_superuser: return True
	if action.startswith('read'):
		if screen is None:
			# every one can access the screen index
			return True
		return screen.type == 'x' or screen.owner == user or (not user.username.startswith('guest_') and screen.type == 'g') or (not isinstance(user, auth.models.AnonymousUser) and screen.type == 'g')
	if action.startswith('delete') or action.startswith('update'):
		if screen is None:
			# only explicitly allowed user can change screen
			return user.has_perm('screendb.add_screen')
		return screen.owner == user

def preescape(text):
	"""pre-escape text so that it is safe without django template's escape.
	Consider <a href="....">...</a> to be safe
	"""
	a = compile(r'<a\s+href="(?#Protocol)(?:(?:ht|f)tp(?:s?)\:\/\/|~\/|\/)?(?#Username:Password)(?:\w+:\w+@)?((?#Subdomains)(?:(?:[-\w\d{1-3}]+\.)+(?#TopLevel Domains)(?:com|org|net|gov|mil|biz|info|mobi|name|aero|jobs|edu|co\.uk|ac\.uk|it|fr|tv|museum|asia|local|travel|[a-z]{2})?)|(?#IP)((\b25[0-5]\b|\b[2][0-4][0-9]\b|\b[0-1]?[0-9]?[0-9]\b)(\.(\b25[0-5]\b|\b[2][0-4][0-9]\b|\b[0-1]?[0-9]?[0-9]\b)){3}))(?#Port)(?::[\d]{1,5})?(?#Directories)(?:(?:(?:\/(?:[-\w~!$+|.,=]|%[a-f\d]{2})+)+|\/)+|\?|#)?(?#Query)(?:(?:\?(?:[-\w~!$+|.,*:]|%[a-f\d{2}])+=?(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)(?:&(?:[-\w~!$+|.,*:]|%[a-f\d{2}])+=?(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)*)*(?#Anchor)(?:#(?:[-\w~!$ |/.,*:;=]|%[a-f\d]{2})*)?"\s*>[^<>]*</a>')
	result = ''
	last_match_end = 0
	m = a.search(text.lower())
	while m:
		result += escape(text[last_match_end:m.start()])
		result += text[m.start():m.end()]
		last_match_end = m.end()
		m = a.search(text, last_match_end)
	result += escape(text[last_match_end:])
	return result
	
def get_all_screens(request):
	"""find all screens one has access to"""
	if request.user.is_superuser:
		screens = Screen.objects.all().order_by("id")
	else:
		if not isinstance(request.user, auth.models.AnonymousUser):
			screens = list(Screen.objects.filter(owner=request.user).order_by("id"))
		else:
			screens = []
		public_s = list(Screen.objects.filter(type='x').order_by("id"))
		for i in public_s:
			if i not in screens:
				screens.append(i)
	return screens

def list_all_screens(request):
	if request.method == 'POST':
		# user uploads a new screen
		# process form upload
		# data is in request.POST
		# first, check if the user can upload
		if not perm(request.user, None, 'update'):
			request.user.message_set.create(
					message="You don't have the permission")
			return HttpResponseRedirect(request.get_full_path())
		s = Screen(owner=request.user)
		user_data = ScreenForm(request.POST, instance=s)
		if user_data.is_valid():
			s = user_data.save()
			return HttpResponseRedirect(s.get_absolute_url())
		else:
			return render_to_response('screen_list.html', dict(
					upload_form=user_data,
					),
					context_instance=RequestContext(request))
				
	else:
		# load screens
		screens = get_all_screens(request)

		for s in screens:
			s.funding = strip_tags(s.funding)

		return render_to_response('screen_list.html', dict(
				screens=screens,
				upload_form=ScreenForm(),
				),
				context_instance=RequestContext(request))

def search(request):
	"""search screen, to be plugged into sitewide search"""
	if request.method == 'POST':
		raise Http404
	query = request.GET['query']
	screens = Screen.search(get_all_screens(request), query)
	for s in screens:
		s.smart_title = "screen #%d: %s" % (s.id, s.name)
	return screens

def delete_screen(request, screen_id):
	if request.method == 'POST':
		screen = Screen.objects.get(id=request.POST['screenid'])
		#if screen.owner == request.user:
		if perm(request.user, screen, 'delete'):
			Screen.objects.get(id=request.POST['screenid']).delete()
			request.user.message_set.create(message=
					"Screen #%s has been deleted" % request.POST['screenid']
			)
			return HttpResponseRedirect(reverse('all-screens'))
		else:
			request.user.message_set.create(message=
					"You don't have permission." 
			)
			return HttpResponseRedirect(
				reverse('screen-detail', kwargs=dict(screen_id=screen_id)))
	else:
		raise Http404

all_form_types = (
	('Publication', PublicationForm),
	('Standard Compound Annotation', StandardCompoundAnnotationForm),
	('Text File', TextFileForm),
	('Image File', ImageFileForm),
	('Annotation File', AnnotationFileForm),
	('Other File', OtherFileForm),
#	('Extra Annotation', ExtraAnnotationForm),
	('Global Reference Image File', GlobalReferenceImageFileForm),
)

def _prepare_file(f):
	"""for each file, do some modification to make it look right"""
	f.description = preescape(f.description)
	# load annotation file content
	if hasattr(f, 'annotationfile'):
		fo = file(f.annotationfile.path.path)
		f.content = fo.read()
		fo.close()
	# whether to show a download button
	f.can_download = hasattr(_load_file(f.id), 'path')

def screen_mod(request, screen):
	"""screen modification request through ajax"""
	if not perm(request.user, screen, 'update'):
		return HttpResponseBadRequest()

	if request.method == 'GET':
   		if request.GET['func'] == 'edit':
			# ajax request to load the form that is used to edit the screen info
			f = ScreenForm(instance=screen)
			return HttpResponse(dumps(dict(
						form=Template("{{form.as_table}}").render(
								Context(dict(form=f)))
						)), mimetype='text/plain')
		elif request.GET['func'] == 'edit-file':
			# ajax request to load the form that is used to edit a screen file
			try:
				screenfile = _load_file(request.GET['fileid'])
				# load the form
				module = __import__('screendb')
				cls = getattr(module.models, screenfile.__class__.__name__ + 'Form')
				f = cls(instance=screenfile)
				return HttpResponse(dumps(dict(
						form=Template("{{form.as_table}}").render(
								Context(dict(form=f)))
						)), mimetype='text/plain')
			except:
				return HttpResponseBadRequest()


	if request.method == 'POST' and 'func' in request.POST:
		if request.POST['func'] == 'edit':
			# editing a screen
			f = ScreenForm(request.POST, instance=screen)
			if f.is_valid():
				f.save()
				return HttpResponse(dumps(dict(status='ok')),
						mimetype='text/plain')
			else:
				return HttpResponse(dumps(dict(
							form=Template("{{form.as_table}}").render(
									Context(dict(form=f)))
							)), mimetype='text/plain')

		if request.POST['func'] == 'edit-file':
				screenfile = _load_file(request.POST['fileid'])
				# load the form
				module = __import__('screendb')
				cls = getattr(module.models, screenfile.__class__.__name__ + 'Form')
				f = cls(request.POST, request.FILES, instance=screenfile)
				if f.is_valid():
					f.save()
					return HttpResponse(dumps(dict(status='ok')),
							mimetype='text/plain')
				else:
					return HttpResponse(dumps(dict(
								form=Template("{{form.as_table}}").render(
										Context(dict(form=f)))
								)), mimetype='text/plain')

		if request.POST['func'] == 'order':
			# update ordering of files
			try:
				fids = request.POST['files'].split(',')
				for i, f in enumerate(fids):
					if not f: continue
					f = ScreenFile.objects.get(id=int(f))
					assert f.screen == screen
					f.ordering = i
					f.save()
				return HttpResponse(
					dumps(dict(status='ok')),
					mimetype='text/plain')
			except:
				return HttpResponseBadRequest()
		
		if request.POST['func'] == 'inactives':
			# reset or upload a list of inactive compounds without uploading
			# a standard compound annotation for them (a simple way to upload
			# inactive information
			# first, manually update screen's last_update timestamp
			# we could capture m2m_changed signal in new Django, but not in 1.1
			screen.save()
			# now clear the old value
			screen.inactive_compounds.clear()
			# if there is file uploaded, set new value
			if 'inactives' in request.FILES:
				# we limit file to 25MB (set in settings.py)
				if request.FILES['inactives'].multiple_chunks():
					return HttpResponse(
						dumps(dict(status='error',
							extended_status='file too large')),
						mimetype='text/plain')
				x = request.FILES['inactives'].read()
				from compounddb.views import _id_to_compound
				for line in x.splitlines():
					lib, cid = line.strip().rsplit(None, 1)
					try:
						c = _id_to_compound(lib, cid)
						screen.inactive_compounds.add(c)
					except: continue
			return HttpResponse(
				dumps(dict(status='ok',
					extended_status='%d compounds now associated' % 
					screen.inactive_compounds.all().count())),
				mimetype='text/plain')
			
def screen_download(request, screen):
	"""support various download operations on screen"""
	if request.GET['download'] in ['ids', 'inactives']:
		# download compound annotated in this screen
		from compounddb.search import add_libname
		if request.GET['download'] == 'ids':
			compounds = Compound.objects.extra(
				tables=['screendb_screenfile'],
				where=['screen_id=%d' % screen.id,
				'compound_id=compounddb_compound.id']
				).distinct()
		else:
			compounds = screen.inactive_compounds.all()
		compounds = add_libname(compounds)
		compounds = compounds.values_list('id', 'libname', 'cid')
		table = '%-15s %-64s %s\n' % ('UNIQUE_ID', 'LIBRARY', 'COMPOUND_ID')
		table += '\n'.join(['%-15s %-64s %s' % i for i in compounds])
		return HttpResponse(table, mimetype='text/plain')
	if request.GET['download'] == 'screen_check':
		from xmldump import check
		f = check(screen) is None
		return HttpResponse(dumps(dict(wait=f)), mimetype='text/plain')
	if request.GET['download'] == 'screen':
		from xmldump import check
		f = check(screen)
		if not f: return HttpResponseBadRequest()
		ff = file(f)
		x = ff.read()
		ff.close()
		r = HttpResponse(x, mimetype='application/octet-stream')
		import os
		r['Content-Disposition'] = 'attachment; filename=%s' % \
			os.path.basename(f)
		return r

def add_score_filter(q, screenid, score1, score2='', score3='',
	table_clause=False):
	"""supply a QuerySet of compounds, apply filter generated by scores in
	standard compound annotations. <score1> could be in format '=1' or '<1'
	or '>1', etc. return the modified queryset"""
	constraint = []
	if score1:
		constraint.append('screendb_standardcompoundannotation.a1_score%s'
			% score1)
	if score2:
		constraint.append('screendb_standardcompoundannotation.a2_score%s'
			% score2)
	if score3:
		constraint.append('screendb_standardcompoundannotation.a3_score%s'
			% score3)

	if not constraint: return q
	tables=['screendb_standardcompoundannotation']
	if table_clause: tables.append('screendb_screenfile')
	return q.extra(
			tables=tables,
			where=constraint + [
				'screendb_standardcompoundannotation.screenfile_ptr_id'\
					'=screendb_screenfile.id',
				'screendb_screenfile.screen_id=%s',
				'screendb_screenfile.compound_id=compounddb_compound.id'],
			params=[screenid]
			)
	

def screen_detail(request, screen_id):
	
	from compounddb.search import (add_libname, add_molecular_weight,
			LibraryHeader)
	try:
		screenid = int(screen_id)
		s = Screen.objects.get(id=screenid)
		if not perm(request.user, s, 'read'):
			raise Http404
	except (Screen.DoesNotExist, ValueError):
		raise Http404

	if ('ajax' in request.GET and 'func' in request.GET) or (
			'ajax' in request.POST and 'func' in request.POST):
		# pass ajax request that modifies the screen to another function
		return screen_mod(request, s)
	
	if 'download' in request.GET:
		# pass download request to another function
		return screen_download(request, s)

	# basic info formatted to be displayed
	s.type = dict(SCREEN_TYPE)[s.type].capitalize()
	s.funding = preescape(s.funding)
	s.description = preescape(s.description)
	# is this a DTS screen?
	s.is_dts = hasattr(screendb.models, 'DTS%dEntry' % screenid)

	# load extra inactive compounds: those without ScreenFiles
	s.extra_inactive = s.inactive_compounds.all().count()
	# load screen-level files: those without associated compounds
	screen_files = s.screenfile_set.filter(compound=None).order_by("ordering", "id")
	# GlobalReferenceImageFile is not subclass of ScreenFile
	try: global_reference = s.globalreferenceimagefile_set.all()[0]
	except: global_reference = None
	# ExtraAnnotation file is not subclass of ScreenFile
	# this is NOT USED
	# extra_annotation = s.extraannotation_set.all()

	# Do we need to limit the display to one specific compound?
	if 'c' in request.GET and request.GET['c']:
		compounds = Compound.objects.filter(id=request.GET['c'])
	else:
		compounds = Compound.objects
	
	# QuerySet for all annotated compounds. this is not evaluated until later
	compounds = compounds.extra(
			select={'min_fid':'''select min(screendb_screenfile.id) from 
			screendb_screenfile where
			screendb_screenfile.compound_id=compounddb_compound.id and
			screen_id=%d''' % screenid},
			tables=['screendb_screenfile'],
			where=['screen_id=%d' % screenid,
			'compound_id=compounddb_compound.id']
			).order_by('min_fid').distinct()

	## load statistics about this screen
	stats = dict()
	## first, try cache
	cache_key = 'screen:stats:%d' % screenid
	if cache.get(cache_key) is not None:
		stats = cache.get(cache_key)
	else:
		# number of compounds annotated
		stats['n_annotated'] = compounds.count()
		# number of libraries annotated
		stats['n_library'] = LibraryHeader.objects.extra(
			tables=['screendb_screenfile',
				'compounddb_compound_library',
				'compounddb_library'],
			where=['compounddb_compound_library.compound_id='\
				'screendb_screenfile.compound_id',
				'compounddb_compound_library.library_id='\
					'compounddb_library.id',
				'compounddb_library.header_id='\
					'compounddb_libraryheader.id',
				'screendb_screenfile.screen_id=%s'],
			params=[screenid]
			).distinct().count()
		# number of active compounds
		stats['n_active'] = add_score_filter(Compound.objects.all(),
				screenid, '>0', table_clause=True).distinct().count()
		# number of inactive compounds
		stats['n_inactive'] = add_score_filter(Compound.objects.all(),
				screenid, '=0', table_clause=True).distinct().count()
		# save to cache
		cache.set(cache_key, stats, 3600 * 24)

	# filter by scores if thresholds are supplied
	thresholds = [request.GET.get('t1', ''),  request.GET.get('t2', ''),\
		 request.GET.get('t3', '')]
	score1, score2, score3 = thresholds
	if score1:
		thresholds[0] = int(score1)
		score1 = '>=' + score1
	if score2:
		thresholds[1] = int(score2)
		score2 = '>=' + score2
	if score3:
		thresholds[2] = int(score3)
		score3 = '>=' + score3
	# first, load the statistics for the score (at each score, how many cmps)
	from screendb.models import ACTIVE_LEVEL_CHOICES
	stats_key = '%s:%s:%s' % (score1, score2, score3)
	if stats_key in stats:
		score_filter_stats = stats[stats_key]
	else:
		score_filter_stats = []
		_ = [add_score_filter(compounds, screenid, '', score2,
				score3).distinct().count(),]
		for i in ACTIVE_LEVEL_CHOICES:
			_.append(add_score_filter(compounds, screenid, '>=%s' % i[0],
						score2, score3).distinct().count())
		score_filter_stats.append(_)
		_ = [add_score_filter(compounds, screenid, score1, '',
				score3).distinct().count(),]
		for i in ACTIVE_LEVEL_CHOICES:
			_.append(add_score_filter(compounds, screenid, score1,
						'>=%s' % i[0], score3).distinct().count())
		score_filter_stats.append(_)
		_ = [add_score_filter(compounds, screenid, score1, score2,
				'').distinct().count(),]
		for i in ACTIVE_LEVEL_CHOICES:
			_.append(add_score_filter(compounds, screenid, score1, score2, 
						'>=%s' % i[0]).distinct().count())
		score_filter_stats.append(_)
		stats[stats_key] = score_filter_stats
		cache.set(cache_key, stats, 3600 * 24)

	# actually apply the filter
	if score1 or score2 or score3: 
		score_filter_on = True
		compounds = add_score_filter(compounds, screenid, score1, score2,
			score3)
	else:
		score_filter_on = False
	
	# adding name information to compounds
	compounds = add_libname(compounds)

	# adding molecular weight from JOELIB
	compounds = add_molecular_weight(compounds)

	# if the user specifies a list of compounds to load, load them without
	# paging
	if 'candidates' in request.GET:
		# we only support ajax request
		if 'ajax' not in request.GET:
			return HttpResponseBadRequest()
		# load these compounds. I know this is slow. Let's keep it simple and
		# hope that it won't be a lot of compounds 
		candidates = []
		from compounddb.views import _id_to_compound
		for _c in request.GET['candidates'].splitlines():
			try:
				compound = _id_to_compound(*_c.split(',', 1))
				candidates.append(compound.id)
			except: pass
		compounds = compounds.filter(id__in=candidates)
		
	else:
		# performing paging
		page = 1
		per_page = 25
		paginator = Paginator(compounds, per_page)
		try:
			page = request.GET.get('page', 1)
			if page == 'last': page = paginator.num_pages
			page = paginator.page(page)
		except:
			raise Http404
		compounds = page.object_list
	
	# actual loading
	compounds = list(compounds)
	
	# load files for these compounds
	files = s.screenfile_set.filter(compound__in=compounds).order_by('ordering', 'id')
	# make sure standard compound annotations appears ealier
	files = [f for f in files if hasattr(f, 'standardcompoundannotation')] + \
			[f for f in files if not hasattr(f, 'standardcompoundannotation')]
	
	for f in files: _prepare_file(f)
	for f in screen_files: _prepare_file(f)

	# reorganize the result
	compounds = [[c, [i for i in files if i.compound == c]] for c in compounds]

	# ready to generate the response now
	# if request is ajax request, only ready the compound files and return in
	# JSON format
	if 'ajax' in request.GET:
		t = get_template('compound_files.html')
		from django.conf import settings 
		context = dict(RENDERER_URL=settings.RENDERER_URL, hideheader=True)
		context['compounds'] = compounds
		resp = dict(html=t.render(Context(context)), n=len(compounds))
		resp['compounds'] = [(c[0].id, c[0].libname + " " + c[0].cid) for c in compounds]
		return HttpResponse(dumps(resp), mimetype='text/plain')
		
	# some extra context
	# 1. did the user click the pager to load this page?
	http_referer = request.META.get('HTTP_REFERER', '')
	if '?' in http_referer: http_referer = http_referer.split('?')[0]
	click_pager = request.GET.get('page', None) is not None and \
			  http_referer.endswith(request.META['PATH_INFO'])

	return render_to_response('screen_detail.html', dict(
			screen=s, stats=stats, compounds=compounds,
			global_reference=global_reference,
			screen_level_files=screen_files, page_obj=page, 
			multipage=paginator.num_pages > 1,
			forms=[(i[0], i[1]()) for i in all_form_types],
			canadd=perm(request.user, s, 'update'),
			candelete=perm(request.user, s, 'delete'),
			click_pager=click_pager,
			thresholds=thresholds, score_filter_on=score_filter_on,
			active_levels=ACTIVE_LEVEL_CHOICES,
			score_filter_stats=dumps(score_filter_stats),
			query_string=request.META['QUERY_STRING'],
			compounds_limited=(request.GET.get('c', False)),
			hideheader=('c' in request.GET and request.GET['c']),
			),
			context_instance=RequestContext(request))
		
def add_file(request, screen_id):
	try: screen_id = int(screen_id)
	except ValueError: raise Http404
	
	screen = get_object_or_404(Screen, id=screen_id)
	if not perm(request.user, screen, 'update'):
		raise Http404
	if request.method == 'GET':
		forms = [(i[0], i[1]()) for i in all_form_types]
		from compounddb.views import all_libraries
		return render_to_response('add_file_standalone.html',
			dict(forms=forms, screen_id=screen_id),
			context_instance=RequestContext(request))
	else:
		form_types = dict(all_form_types)
		form_type = request.POST['type']
		ajax = 'ajax' in request.POST
		if form_type not in form_types: raise Http404
		form_cls = form_types[form_type]
		model_cls = form_cls.Meta.model
		model_inst = model_cls(screen=screen)
		f = form_cls(request.POST, request.FILES, instance=model_inst)
		if f.is_valid():
			upload = f.save()
			# note that we should escape HTML from file and pre-escape
			# things like description, etc, as when the file is loaded
			# in general cases. However, since it is the uploader that
			# sees the result now, we will not care about these suicide
		 	# cases.
			if ajax:
				# ajax response to add file request
				# prepare different response based on whether the upload
				# is a compound file or screen-level file
				_prepare_file(upload)
				context = dict()
				if hasattr(upload, 'compound') and upload.compound:
					# load compound information
					upload.compound.libname = \
						upload.compound.library.select_related('header'
						).latest().header.name
					# use compound_file.html as the template
					t = get_template('compound_files.html')
					# format the data as required by the template
					context['compounds']=[(upload.compound, [upload])]
				else:
					# a screen level file is uploaded
					t = get_template('screen_level_files.html')
					# put files in a list as required by the template
					context['screen_level_files'] = [upload]
				# add general context
				from django.conf import settings 
				context.update(dict(
					RENDERER_URL=settings.RENDERER_URL,
					hideheader=True))
				# build the full response in a dictionary, ready to be
				# converted in JSON format
				resp = dict(file=t.render(Context(context)),
							form=Template("{{form.as_table}}").render(
							Context(dict(form=form_cls()))),
							has_compound=upload.compound is not None)
				return HttpResponse(dumps(resp), mimetype='text/plain')
			else:
				return HttpResponseRedirect(
					reverse('screen-detail', kwargs=dict(screen_id=screen_id)))
		else:
			if ajax:
				resp = dict(form=Template("{{form.as_table}}").render(
							Context(dict(form=f))))
				return HttpResponse(dumps(resp), mimetype='text/plain')
			else:
				return render_to_response('add_file_standalone.html',
					dict(form=f, type=form_type, screen_id=screen_id),
					context_instance=RequestContext(request))

def delete_file(request, file_id, typehint):
	try:
		if typehint == 'ref':
			f = GlobalReferenceImageFile.objects.get(id=file_id)
		else:
			f = ScreenFile.objects.get(id=file_id)
	except (ScreenFile.DoesNotExist, GlobalReferenceImageFile.DoesNotExist,
		ValueError):
		raise Http404
	screen = f.screen
	if perm(request.user, screen, 'delete'):
		f.delete()
		request.user.message_set.create(message=
				"File has been deleted." 
		)
	else:
		request.user.message_set.create(message=
				"You don't have permission." 
		)

	return HttpResponseRedirect(
		reverse('screen-detail', kwargs=dict(screen_id=screen.id)))

def _load_file(file_id):
	"""given the file_id, load the screen file and cast to the correct type"""
	f = ScreenFile.objects.get(id=file_id)
	if hasattr(f, 'textfile'):
		f = f.textfile
	elif hasattr(f, 'imagefile'):
		f = f.imagefile
	elif hasattr(f, 'annotationfile'):
		f = f.annotationfile
	elif hasattr(f, 'otherfile'):
		f = f.otherfile
	elif hasattr(f, 'publication'):
		f = f.publication
	elif hasattr(f, 'standardcompoundannotation'):
		f = f.standardcompoundannotation
	else:
		raise ValueError
	return f

def serve_file(request, file_id, typehint=''):
	# TODO: for performance improvement, consider rewrite using X-Sendfile
	if request.method == 'POST':
		if 'delete' in request.POST:
			return delete_file(request, file_id, typehint)
		else:
			return HttpResponseBadRequest()
	else:
		if typehint == 'ref':
			# server global reference image
			f = GlobalReferenceImageFile.objects.get(id=file_id)
		else:
			# serve ScreenFile-subclass objects
			try:
				f = _load_file(file_id)
				assert f.path is not None
			except:
				raise Http404
		
		screen = f.screen
		if perm(request.user, screen, 'read-file'):
			if isinstance(f, ImageFile) and typehint == 'locref':
				path = f.reference.path
			else:
				path = f.path.path
			f_ = file(path)
			c = f_.read()
			f_.close()
			r = HttpResponse(c, content_type=f.mime)
			if 'download' in request.GET:
				r['Content-Disposition'] = 'attachment; filename=%s' %\
					f.original_name
			return r
		else:
			raise Http404

def find_dts_page(request, dts_cls):
	"""given request DTS screen, find the page number for redirection if
	necessary. Currently it check whether 'find' (finding a compound) or
	'plate' is in the query.
	"""
	cache_key = 'screen:dts:plates:%s' % dts_cls.__name__
	if cache.get(cache_key) is not None:
		all_plates = cache.get(cache_key)
	else:
		all_plates = dts_cls.objects.all().order_by('plate')\
			.values_list('plate').distinct()
		cache.set(cache_key, all_plates, 300)
	# determine which page/plate to load
	plate = None
	page = 0
	# is a compound given?
	c = None
	if request.GET.get('find', False):
		c = Compound.objects.get(id=request.GET['find'])
		for entry in getattr(c, 'dtsentry_set').all():
			if hasattr(entry, dts_cls.__name__.lower()):
				plate = entry.plate
	if plate is None:
		plate = request.GET.get('plate', False)
	# from plate to page
	if plate:
		# lookup the page number
		page = 0
		for i, _plate in enumerate(all_plates):
			if _plate[0].lower() == plate.lower():
				page = i + 1
				break
		if not page:
			raise Http404
	return page, c, all_plates


def dts(request, screen_id):
	from django.views.generic.list_detail import object_list
	cls = getattr(screendb.models, 'DTS%dEntry' % int(screen_id))
	# check implicit paging
	page, c, all_plates = find_dts_page(request, cls)
	if page:
		if c:
			return HttpResponseRedirect(request.path + '?page=%d&hl=%d' %
					(page, c.id))
		else:
			return HttpResponseRedirect(request.path + '?page=%d' % page)

	queryset = cls.objects.all()

	# limit to a compound?
	compound = request.GET.get('c', False)
	if compound:
		queryset = queryset.filter(compound=compound)
		page_obj, paginator = None, None
	else:
		# paging is done per plate
		all_plates = cls.objects.all().order_by('plate')\
			.values_list('plate').distinct()
		paginator = Paginator(all_plates, 1)

		page = 1
		try:
			page = request.GET.get('page', 1)
			if page == 'last': page = paginator.num_pages
		except:
			raise Http404
		page = paginator.page(page)
		plate = page.object_list[0][0]

		# load entries in this plate
		queryset = queryset.filter(plate=plate)

	# highlight any compound?
	highlight = 0
	if request.GET.get('hl', False):
		try:
			highlight = int(request.GET['hl'])
		except:
			pass
	return object_list(request, queryset,
			template_name="dts.html",
			extra_context=dict(
				screen_id=screen_id,
				cls=cls,
				highlight=highlight,
				compound=compound,page_obj=page,
				paginator=paginator,
				all_plates=all_plates,
			))

def virtualplate(request, screen_id):
	cls = getattr(screendb.models, 'DTS%dEntry' % int(screen_id))
	# check implicit paging
	page, c, all_plates = find_dts_page(request, cls)
	if page:
		return HttpResponseRedirect(request.path + '?page=%d' % page)

	# aggregation
	from django.db.models import Min, Max
	aggregated_field = [Min(x) for x in cls.Info.virtual_plate_fields] + \
		[Max(x) for x in cls.Info.virtual_plate_fields]
	# global min max
	g_min_max = cls.objects.all().aggregate(*tuple(aggregated_field))
	# convert to float coz json does not understand decimal
	g_min_max = dict([(k, float(v)) for k, v in g_min_max.items()])

	# load by plate. a trick is to page by plate and show one plate per page
	all_plates = cls.objects.all().order_by('plate')\
		.values_list('plate').distinct()
	paginator = Paginator(all_plates, 1)

	page = 1
	try:
		page = request.GET.get('page', 1)
		if page == 'last': page = paginator.num_pages
	except:
		raise Http404
	page = paginator.page(page)
	plate = page.object_list[0][0]

	# load entries in this plate
	entries = cls.objects.filter(plate=plate)
	welldata = dict()
	anywell = None
	for entry in entries:
		welldata[entry.well] = entry
	# convert to format ready to be placed into HTML table
	all_data = dict([ (field, dict()) for field in cls.Info.virtual_plate_fields ])
	plate_data = []
	plate_format = cls.Info.per_plate
	if plate_format == 384:
		x, y = 16, 24
	elif plate_format == 96:
		x, y = 8, 12
	for row in range(x):
		rowdata = [chr(65 + row), []]
		for column in range(y):
			well = '%s%02d' % (chr(65 + row), column + 1)
			rowdata[1].append((well, unicode(welldata.get(well, ''))))
			# store the actual data for lookup
			for field in cls.Info.virtual_plate_fields:
				try:
					all_data[field][well] = float(getattr(welldata[well], field))
					anywell = well
				except KeyError:
					pass
		plate_data.append(rowdata)
		colnames = ['%02d' % (column + 1) for column in range(y)]

	return render_to_response('dts-vp.html',
		dict(plate_data=plate_data, columns=cls.Info.virtual_plate_fields,
		screen_id=screen_id, g_min_max=dumps(g_min_max),
		all_data=dumps(all_data), colnames=colnames, page_obj=page,
		paginator=paginator, anywell=anywell, all_plates=all_plates,),
		context_instance=RequestContext(request))


