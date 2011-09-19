""" to add an compound level standard annotation file 
	for an existing screen """
""" only Assay 1 is processed, ignore Assay 2 and Assay 3"""
""" can be run on chemmine or development server, as no file is to be 
	stored """

import sys
import os
import shutil

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from screendb.models import Screen, StandardCompoundAnnotation
from compounddb.models import Compound
from compounddb.views import get_library_by_name

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-d", "--desc", dest="description",)
parser.add_option("-a", "--anno", dest="extra_annotation")
parser.add_option("-n", "--name", dest="assay_name")

(options, args) = parser.parse_args()

# the last two are optional arguments
screenid = int(sys.argv[1])
libname = sys.argv[2]
cid = sys.argv[3]
a1_score = sys.argv[4] # integer: 0-5
a1_concentration = sys.argv[5]
a1_name = options.assay_name
description = options.description
extra_annotation = options.extra_annotation

if not a1_name:
	a1_name = ''
if not description:
	description = 'None'
if not extra_annotation:
	extra_annotation = ''

lib = get_library_by_name(libname)
compound = Compound.objects.get(cid__iexact=cid, library=lib)

s = Screen.objects.get(id=screenid)
StandardCompoundAnnotation(
	screen=s,
	compound=compound,
	a1_name=a1_name,
	a1_desc=description,
	a1_score=int(a1_score),
	a1_concentration=a1_concentration,
	mime='text/annotation',
	extra_annotation=extra_annotation,
).save()

