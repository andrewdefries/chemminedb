"""script to migrate screen data from ChemMineV2 to ChemMine NG. To be used
with pickledump.py, which dumps screen data out of ChemMineV2"""

# make it possible to run as standalone program
import sys
sys.path.append('..')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from time import sleep

def format_tree(s, level=0):
	if s is None: return ''
	r = []
	for i in s:
		r.append(' ' * level + i[0].strip() + ': ' + i[1].strip())
		if i[2]: r.append(format_tree(i[2], level+1))
	return '\n'.join(r)

# loading data from file specified on the command line
from pickle import load
f = file(sys.argv[1])
screen, files, compounds, reference, owner = load(f)
f.close()

# ready to write
from screendb.models import Screen, User, StandardCompoundAnnotation, \
	ImageFile, TextFile, GlobalReferenceImageFile, Publication, OtherFile,\
	AnnotationFile
from compounddb.models import Compound
from compounddb.views import get_library_by_name
u = User.objects.get(id=1)

# create the screen
s = Screen(
	id=screen['number'],
	owner=u,
	name=screen['name'],
	description=screen['description'],
	pi=screen['PI'],
	co_author=screen.get('co-author', ''),
	funding=screen.get('funding', ''),
	number_of_cmp_screened=screen.get('compounds screened', None),
	strategy=format_tree(screen.get('evidence')),
	type=dict(public='x', group='g', private='o')[screen['status']],
	extra_annotation=format_tree(screen['annotation_tree'])
	)
s.save()

popped = dict()
popped_used = False

# create the files with associated compounds
for c in compounds.values():
	lib = get_library_by_name(c['name'][0][0])
	compound = Compound.objects.get(cid__iexact=c['name'][0][1], library=lib)
	print 'found %s:%s' % c['name'][0]
	# if there is assay data, convert to standard compound annotation
	if 'assays' in c:
		f = c['assays']
		StandardCompoundAnnotation(
			screen=s,
			title=f['title'],
			compound=compound,
			description=f['description'],
			mime='text/annotation',
			original_name=f['original name'],
			extra_annotation=format_tree(f['annotation_tree']),
			a1_name=f['content'][0]['name'],
			a1_desc=f['content'][0]['description'],
			a1_score=f['content'][0]['score'],
			a1_concentration=f['content'][0]['concentration']
			).save()
	# other data
	for fid in c['files']:
		if fid in files:
			f = files.pop(fid)
			popped[fid] = f
		else:
			f = popped[fid]
			popped_used = True
		mime = f['mime']
		if mime == 'compound_annotation': continue
		print mime
		if mime.startswith('image'):
			# if compound with id=<fid> already exists, don't set the id
			try:
				i = ImageFile.objects.get(id=fid)
				ImageFile(
					screen=s,
					title=f['title'],
					compound=compound,
					description=f['description'],
					mime=mime,
					original_name=f['original name'],
					extra_annotation=format_tree(f['annotation_tree']),
					path='import/%d/%s' % (s.id, f['original name'])
				).save()
			except ImageFile.DoesNotExist:
				ImageFile(
					screen=s,
					id=fid,
					title=f['title'],
					compound=compound,
					description=f['description'],
					mime=mime,
					original_name=f['original name'],
					extra_annotation=format_tree(f['annotation_tree']),
					path='import/%d/%s' % (s.id, f['original name'])
				).save()
		elif mime == 'URL':
			if s.id == 252:
				Publication(
					screen=s,
					id=fid,
					title=f['title'],
					compound=compound,
					description=f['description'],
					mime='',
					original_name='',
					web_url=f['path'],
					mode='web',
				).save()

			elif 'url_mode' not in f or f['url_mode'] == 'publication':
				Publication(
					screen=s,
					id=fid,
					mode='publication',
					title=f['title'],
					compound=compound,
					description=f['description'],
					mime='',
					original_name='',
					journal=f['journal appeared in'],
					volume=f['article pages'].split(':')[0],
					pages=f['article pages'].split(':')[0],
					pub_title=f['article title'],
					author=f['article author'],
					publication_url=f['path']
				).save()
			else:
				raise
		elif mime.startswith('text'):
			TextFile(
				screen=s,
				id=fid,
				title=f['title'],
				compound=compound,
				description=f['description'],
				mime=mime,
				original_name=f['original name'],
				extra_annotation=format_tree(f['annotation_tree']),
				path='import/%d/%s' % (s.id, f['original name'])
			).save()
		elif mime.startswith('application'):
			OtherFile(
				screen=s,
				id=fid,
				title=f['title'],
				compound=compound,
				description=f['description'],
				mime=mime,
				original_name=f['original name'],
				extra_annotation=format_tree(f['annotation_tree']),
				path='import/%d/%s' % (s.id, f['original name'])
			).save()
		elif mime == 'annotation':
			AnnotationFile(
				screen=s,
				id=fid,
				title=f['title'],
				compound=compound,
				description=f['description'],
				mime='',
				original_name=f['original name'],
				extra_annotation=format_tree(f['annotation_tree']),
				path='import/%d/%s' % (s.id, f['original name'])
			).save()
		else:
			raise

for fid in files:
	f = files[fid]
	mime = f['mime']
	print mime
	if mime == 'compound_annotation': continue
	if mime.startswith('image'):
		if 'reference' in screen and f['number'] == screen['reference']:
			GlobalReferenceImageFile(
				screen=s,
				id=fid,
				mime=mime,
				path='import/%d/%s' % (s.id, f['original name'])
			).save()
		else:
			ImageFile(
				screen=s,
				id=fid,
				title=f['title'],
				description=f['description'],
				mime=mime,
				original_name=f['original name'],
				extra_annotation=format_tree(f['annotation_tree']),
				path='import/%d/%s' % (s.id, f['original name'])
			).save()
	elif mime == 'URL':
		if f['url_mode'] == 'publication':
			Publication(
				screen=s,
				id=fid,
				title=f['title'],
				description=f['description'],
				mime='',
				original_name='',
				mode='publication',
				journal=f['journal appeared in'],
				volume=f['article pages'].split(':')[0],
				pages=f['article pages'].split(':')[0],
				pub_title=f['article title'],
				author=f['article author'],
				publication_url=f['path']
			).save()
	elif mime.startswith('text'):
		TextFile(
			screen=s,
			id=fid,
			title=f['title'],
			description=f['description'],
			mime=mime,
			original_name=f['original name'],
			extra_annotation=format_tree(f['annotation_tree']),
			path='import/%d/%s' % (s.id, f['original name'])
		).save()
	else:
		raise
	
if popped_used:
	print "some files used more than once"
