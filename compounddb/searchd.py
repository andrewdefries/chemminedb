#!/usr/bin/env python2.5
"""dedicated search script to be used as a daemon"""
import os
mydir = os.path.dirname(__file__)
project_dir = os.path.join(mydir, '..')
import sys
sys.path.append(project_dir)

WORK_DIR = os.path.join(project_dir, 'working')

if __name__ == '__main__':
	from django.utils.daemonize import become_daemon
	become_daemon()
	os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
	from search import struct_search

	os.chdir(WORK_DIR)
	hash = sys.argv[1]
	os.chdir(hash)
	from pickle import load, dump

	f = file('in')
	sdf, libs = load(f)
	f.close()
	compounds = struct_search(sdf, libs)
	f = file('out.', 'w')
	dump(compounds, f)
	f.close()
	from shutil import move
	move('out.', 'out')

