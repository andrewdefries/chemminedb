#!/usr/bin/env python2.5
"""dump a screen to a folder with XML and data files. This runs as a daemon"""
import os
mypath = os.path.abspath(__file__)
if mypath.endswith('.pyc'): mypath = mypath[:-1]
mydir = os.path.dirname(mypath)
project_dir = os.path.join(mydir, '..')
import shutil
import sys
from datetime import datetime
import stat
sys.path.append(project_dir)

WORK_DIR = os.path.join(project_dir, 'working')
screen_xml_dir = os.path.join(WORK_DIR, 'screen-downloads')

def check(screen):
	"""check if the screen is ready to be downloaded; if not, return None
	and invoke the dump process"""
	fname = os.path.join(screen_xml_dir, 'screen-%s.tar.bz2' % screen.id)
	ready = os.path.isfile(fname) and \
		datetime.fromtimestamp(os.stat(fname)[stat.ST_CTIME]) > \
		screen.last_update
	if not ready:
		os.system('%s %d' % (mypath, screen.id))
		return None
	return fname

def dump(sid):
	# making the placeholder file; making sure at most one instance is running
	fname = os.path.join(screen_xml_dir, 'screen-%s.tar.bz2' % sid)
	fname_st = os.path.join(screen_xml_dir, 'screen-%s.working' % sid)
	if os.path.exists(fname_st):
		sys.exit(0)
	os.system('touch %s' % fname_st)

	try:
		# loading kid template
		import kid
		exec_dir = mydir
		mod = kid.load_template(os.path.join(exec_dir, "screenxml.kid"))

		# making a folder to store data
		if os.path.exists('screen-%s' % sid):
			shutil.rmtree('screen-%s' % sid)
		shutil.os.mkdir('screen-%s' % sid)
		shutil.os.mkdir(os.path.join('screen-%s' % sid, 'data'))

		# loading the screen
		sys.stderr.write("loading screen #%s...\n" % sid)
		from screendb.models import Screen, Compound, StandardCompoundAnnotation, Publication
		try:
			s = Screen.objects.get(id=sid)
		except Screen.DoesNotExist:
			sys.stderr.write("Screen #%d cannot be loaded.\n" % sid)
			raise


		# loading files, compounds and special files
		files = s.screenfile_set.all()
		compounds = Compound.objects.filter(screenfile__screen=s)
		inactives = s.inactive_compounds.all()
		from compounddb.search import add_libname
		compounds = add_libname(compounds)
		inactives = add_libname(inactives)
		try:
			reference = s.globalreferenceimagefile_set.all()[0]
		except:
			reference = None
		compounds = list(compounds)

		sys.stderr.write("loaded!\n")

		# data structure to hold results
		screen_level_files = []
		compound_files = dict([(c.id, []) for c in compounds])
		standardcompoundannotation = dict()
		compound_oldest_file = dict([(c.id, None) for c in compounds])
		
		from screendb.views import _load_file
		copied = dict()
		for f in files:
			ff = _load_file(f.id)
			if ff.compound:
				c = ff.compound.id
				if isinstance(ff, StandardCompoundAnnotation):
					standardcompoundannotation[c] = ff
				else:
					compound_files[c].append(ff)
				if compound_oldest_file[c] is None or \
					compound_oldest_file[c] > ff.id:
					compound_oldest_file[c] = ff.id
			else:
				screen_level_files.append(ff)

			def _copy(fid, fpath, suggested_name):
				if not fpath in copied:
					sys.stderr.write("copying %s\n" % fpath)
					name = "%d-%s" % (
						fid, suggested_name)
					shutil.copy(fpath,
						os.path.join(
							'screen-%s' % sid,
							'data',
							name
						)
					)
					copied[fpath] = name
				return copied[ff.path.path]

			if hasattr(ff, 'path'):
				ff.fname = _copy(ff.id, ff.path.path, ff.original_name)
			if hasattr(ff, 'reference') and ff.reference:
				ff.reference_name = _copy(ff.id, ff.reference.path, 'reference')

		# ordering the compounds
		compounds.sort(key=lambda x:compound_oldest_file[x.id])
		template = mod.Template(
				screen=s, compounds=compounds,reference=reference,
				inactives=inactives,
				screen_level_files=screen_level_files,
				compound_files=compound_files,
				standardcompoundannotation=standardcompoundannotation,
				Publication=Publication)
		template.assume_encoding = 'utf-8'
		results = template.serialize(output='xml')

		of = file(
					os.path.join(
						'screen-%s' % sid,
						'screen.xml'
					)
				, 'w')
		for i in results:
			of.write(i)
		of.close()

		sys.stderr.write("compressing...\n")
		status = os.system('tar -cjf screen-%s.tar.bz2 screen-%s > /dev/null' % (sid, sid))
		if status == 0:
			sys.stderr.write("removing working folder\n")
			os.system('rm -rf screen-%s' % sid)
			os.system('mv screen-%s.tar.bz2 %s' % (sid, fname))
			os.unlink(fname_st)
	except:		
			os.unlink(fname_st)
			raise

if __name__ == '__main__':
	from django.utils.daemonize import become_daemon
	become_daemon()
	os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

	os.chdir(WORK_DIR)

	try:
		sid = int(sys.argv[1])
	except:
		sys.stderr.write("Usage: %s screen-id\n" % sys.argv[0])
		sys.exit(1)
	dump(sid)
