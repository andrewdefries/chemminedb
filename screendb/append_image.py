""" to add an compound level image file for an existing screen """
""" to be run on chemmine, as image file is to be 
	stored on chemmine server"""

import sys
import os
import shutil

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from screendb.models import Screen,	ImageFile
from compounddb.models import Compound
from compounddb.views import get_library_by_name

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-t", "--title", dest="title")
parser.add_option("-d", "--desc", dest="description",)
parser.add_option("-a", "--anno", dest="extra_annotation")

(options, args) = parser.parse_args()

# the last three are optional arguments
screenid = int(sys.argv[1])
fname = sys.argv[2]
libname = sys.argv[3]
cid = sys.argv[4]
title = options.title
description = options.description
extra_annotation = options.extra_annotation

original_name = os.path.basename(fname)
suffix = os.path.splitext(original_name)[1].lower()
if  suffix == '.jpg':
	mime = 'image/jpeg'
elif suffix == '.gif':
	mime = 'image/gif'
elif suffix == '.png':
	mime = 'image/png'

if not title:
	title = ''
if not description:
	description = original_name
if not extra_annotation:
	extra_annotation = ''

lib = get_library_by_name(libname)
compound = Compound.objects.get(cid__iexact=cid, library=lib)

s = Screen.objects.get(id=screenid)
ImageFile(
	screen=s,
	title=title,
	compound=compound,
	description=description,
	mime=mime,
	original_name=original_name,
	extra_annotation=extra_annotation,
	path='import/%d/%s' % (s.id, original_name)
).save()

# save image file on chemmine server
src_path='%s/uploads/import/%d' % (project_root, s.id)
if not os.path.isdir(src_path):
	shutil.os.mkdir(src_path)
shutil.copyfile(fname, '%s/%s' % (src_path, original_name))

