from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from compounddb import first_mol, InvalidInputError
from compounddb.search import search
from compounddb.views import get_library_by_name
from compounddb.tools import parse_annotation, insert_single_compound
from compounddb.models import Compound
from myCompounds.DownloadCIDs import DownloadCIDs
from compounddb.models import WorkbenchCompounds
import random
import openbabel
import re

try:
	from moleculeformats import smiles_to_sdf, sdf_to_sdf, InputError, sdf_to_smiles
except:
	import sys
	sys.path.append('/home/ycao/sdftools')
	from moleculeformats import smiles_to_sdf, sdf_to_sdf, InputError, sdf_to_smiles

def uploadCompound(request, *args, **kargs):
    # perform query for existing myCompounds
    page, matches = getMyCompounds(request)
    if request.method == 'GET':
        return render_to_response('submitCompound.html', dict(p=page, matches=matches,), context_instance=RequestContext(request))    
    else:
		sdf = None
		name = None
		compid = None
		smiles = None
		if 'deleteSelected' in request.POST:
		    input_mode = 'view'
		    cids = request.POST.getlist(u'array')
		    if cids:
		        deleteMyCompounds(request.user.username, cids)
		        request.user.message_set.create(message=
		            "Selected Compounds Deleted!"
					)
				# re-perform query to get non-deleted list
		        page, matches = getMyCompounds(request)
		    else:
		        request.user.message_set.create(message=
		            "No Compounds Selected for Deletion!"
					)
		if 'sendTools' in request.POST:
		    input_mode = 'view'
		    cids = request.POST.getlist(u'array')
		    if cids:
		        addToWorkbench(request.user.username, cids)
		        request.user.message_set.create(message=
		            "Selected Compounds sent to Tools!"
					)
				# re-perform query to get non-deleted list
		        page, matches = getMyCompounds(request)
		    else:
		        request.user.message_set.create(message=
		            "No Compounds Selected!"
					)
		if 'deleteAll' in request.POST:
		    input_mode = 'view'
		    deleteMyCompounds(request.user.username)
		    matches = None
		    request.user.message_set.create(message=
					"All Compounds Deleted!"
					)
		if 'smiles' in request.POST:
			input_mode = 'smiles-input'
			try:
				sdf = smiles_to_sdf(str(request.POST['smiles']))
				smiles = str(request.POST['smiles'])
				name = str(request.POST['name'])
				compid = str(request.POST['id'])
			except InputError:
				request.user.message_set.create(message=
					"Invalid SMILES string!"
				)
				sdf = None
		elif 'sdf' in request.FILES:
			input_mode = 'sdf-upload'
			try:
				# sdf = first_mol(request.FILES['sdf'])
				# sdf = sdf_to_sdf(sdf)
				sdf = request.FILES['sdf']
				sdf = sdf.read()
			except (InputError, InvalidInputError):
				request.user.message_set.create(message=
					"Invalid SDF!"
				)
				sdf = None
		elif 'sdf' in request.POST:
			if 'draw' in request.POST:
				input_mode = 'draw'
				sdf = request.POST['sdf'] + '$$$$'
				name = str(request.POST['name'])
				compid = str(request.POST['id'])
				# assert False, 'ok'
				try:
					# sdf = batch_sdf_to_sdf(sdf)
					# sdf = first_mol(request.POST['sdf'])
					# sdf = sdf_to_sdf(sdf)
					sdf = request.POST['sdf'] + '$$$$' # add data checks here
				except (InputError, InvalidInputError):
					request.user.message_set.create(message=
						"Invalid SDF!"
					)
					sdf = None
			else:
				input_mode = 'sdf-input'
				sdf = request.POST['sdf']
		elif 'pubchem' in request.POST:
		    cids = request.POST['pubchem']
		    cids = cids.split()
		    input_mode = 'pubchem'
		    filteredCIDs = []
		    for cid in cids[:]:
		        match = re.search("(\d{1,200})", cid)
		        if match:
		        	filteredCIDs.append(int(match.group(1)))

		    if (len(filteredCIDs) > 0):
			try:
				sdf = DownloadCIDs(filteredCIDs)
			except:
				request.user.message_set.create(message=
                       			 "Invalid CIDs or no response from PubChem!"
					)
				sdf = None
		    else:
				request.user.message_set.create(message="Error: No valid CIDs entered!")
				sdf = None
		    
		if not sdf:
			return render_to_response('submitCompound.html', dict(
				input_mode=input_mode,
				post_data=request.POST,
				p=page,
				matches=matches,
				),
				context_instance=RequestContext(request))
		# if input_mode == 'pubchem':
		addMyCompounds(sdf, request.user.username,name,compid, smiles)
        # re-perform query to get newly added compounds
		page, matches = getMyCompounds(request)

		return render_to_response('submitCompound.html', dict(p=page, matches=matches,),
			context_instance=RequestContext(request))

def getMyCompounds(request):
	page = int(request.GET.get('p', '1'))
	matches = []
	pure_query, matches = search('library: myCompounds', page, request)
	if len(matches[0][1]) == 0:
		matches = None
	return page, matches

def addMyCompounds(sdf, username, name=None, compid=None, smiles=None):
	library = get_library_by_name('myCompounds')
	sdffile = u''
	namekey = 'PUBCHEM_IUPAC_NAME'
	idkey = 'PUBCHEM_COMPOUND_CID'
	# assert False, sdf
	sdf = sdf.split("\n")
	for line in sdf:
		# line = unicode(line, 'latin1')
		sdffile += line
		sdffile += '\n'
		if line.startswith("$$$$"):
			try: 
				moldata = parse_annotation(sdffile, namekey, idkey)			
			except (KeyError):
				moldata = {}
				random.seed()
				if name and name != '':
					moldata[namekey] = name
				else:
					moldata[namekey] = 'random' + str(random.randint(10000000, 90000000))
				if compid and compid != '':
					moldata[idkey] = compid
				else:
					moldata[idkey] = 'random' + str(random.randint(10000000, 90000000))
				moldata['formula'] = getFormula(sdffile)
				moldata['weight'] = getMW(sdffile)
				moldata['inchi'] = getInChI(sdffile)
				if smiles and smiles != '':
					moldata['smiles'] = smiles
				else:
					moldata['smiles'] = sdf_to_smiles(sdffile)
			# verify that compound id doesn't already exist, if it does append "_2" tail
			while True:
				try:
					idsearch = Compound.objects.get(cid__iexact=moldata[idkey].strip(), library=library)
				except:
				    # search will call an exception IF the compound doesn't already exist
					insert_single_compound(moldata, sdffile, library, namekey, idkey, username)
					break
				else:
					moldata[idkey] = moldata[idkey] + '_2'
			sdffile = u''
			
def getMW(sdf):
	if isinstance(sdf, unicode):
		sdf = sdf.encode('ascii', 'ignore')
	
	obConversion = openbabel.OBConversion()
	obConversion.SetInAndOutFormats("sdf", "smi")
	mol = openbabel.OBMol()
	if not obConversion.ReadString(mol, sdf):
		raise InputError
	return str(mol.GetMolWt())
    
def getFormula(sdf):
	if isinstance(sdf, unicode):
		sdf = sdf.encode('ascii', 'ignore')
	
	obConversion = openbabel.OBConversion()
	obConversion.SetInAndOutFormats("sdf", "smi")
	mol = openbabel.OBMol()
	if not obConversion.ReadString(mol, sdf):
		raise InputError
	return str(mol.GetFormula())
	
def getInChI(sdf):
	if isinstance(sdf, unicode):
		sdf = sdf.encode('ascii', 'ignore')
	
	obConversion = openbabel.OBConversion()
	obConversion.SetInAndOutFormats("sdf", "InChI")
	mol = openbabel.OBMol()
	if not obConversion.ReadString(mol, sdf):
		raise InputError
	return obConversion.WriteString(mol)

def deleteMyCompounds(username=None, cids=None):
    if username:
        library = get_library_by_name('myCompounds')
        compoundsToDelete = Compound.objects.filter(library=library)
        compoundsToDelete = compoundsToDelete.filter(username=username)
        if cids:
            for cid in cids:
                Compound.objects.filter(cid=cid).delete()
        else:
        	compoundsToDelete.delete()
        	
def addToWorkbench(username, cids):
    library = get_library_by_name('myCompounds')
    for cid in cids:
        compound = WorkbenchCompounds(compound = Compound.objects.get(cid__iexact=cid, library=library), username = username)
        compound.save()
