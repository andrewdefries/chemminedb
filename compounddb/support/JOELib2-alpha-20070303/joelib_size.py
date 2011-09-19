import sys, re
import tempfile
import os


joelibcolumns = [ 
	("LogP", 31),
	("Number_of_HBA_1", 2),
	("Number_of_HBA_2", 3),
	("Number_of_HBD_1",24),
	("Number_of_HBD_2",25),
	("Number_of_acidic_groups", 27),
	("Number_of_aliphatic_OH_groups", 11), 
	("Number_of_basic_groups", 16),
	("Fraction_of_rotatable_bonds", 1),
	("Number_of_heavy_bonds", 28),
	("Number_of_heterocycles", 36),
	("Number_of_hydrophobic_groups", 30),
	("MolarRefractivity", 4),
	("Number_of_atoms", 20),
	("Number_of_halogen_atoms", 29),
	("Number_of_B_atoms", 27), 
	("Number_of_Br_atoms", 19),
	("Number_of_Cl_atoms", 12),
	("Number_of_I_atoms", 33), 
	("Number_of_F_atoms", 15),
	("Number_of_N_atoms", 13),
	("Number_of_O_atoms", 8),
	("Number_of_P_atoms", 17),
	("Number_of_S_atoms", 18),
	("Number_of_bonds", 9),
	("Number_of_NO2_groups", 14),
	("Number_of_SO_groups", 10),
	("Number_of_OSO_groups", 32),
	("Number_of_SO2_groups", 37),
	("PolarSurfaceArea", 7),
	("Geometrical_diameter", 22),
	("Geometrical_radius", 21),
	("Geometrical_shape_coefficient", 23),
	("Kier_shape_1", 34),
	("Kier_shape_2", 35),
	("Zagreb_group_index_1", 5),
	("Zagreb_group_index_2", 6),
]

joelibcolumns.sort(key=lambda x: x[1])

def get_sdf_tags(sdf):
	"""parse the sdf tags"""
	tag_pattern = re.compile(">\s+<([^>]+)>([^>$]+)", re.DOTALL)
	tags = tag_pattern.findall(sdf)
	tagdict = dict()
	#process each tag
	for name, value in tags:
		tagdict[name.strip()] = value.strip()
	return tagdict

def gen_joelib(sdf):

	# prepare the output file
	(f, out) = tempfile.mkstemp(suffix=".sdf")
	os.close(f)

	# convert
	#cmd = '/usr/local/opt/JOELib/convert.sh +d -iSDF -oSDF "%s" "%s"' % (
	#		sdf, out)
	cmd = 'JAVA_HOME=/usr/lib/jvm/java-1.5.0-sun/jre/ JOELIB2=/home/lwang/JOELib2-alpha-20070303 /home/lwang/JOELib2-alpha-20070303/moleculeConversion.sh +d -iSDF -oSDF "%s" "%s"' % (sdf, out)
	os.system(cmd)

	# read and parse
	f = file(out)
	tags = get_sdf_tags(f.read())
	f.close()

	# clean
	os.unlink(out)

	return tags

if __name__ == "__main__":

	iid_fp = file(sys.argv[1])

	counter = 0
	for i in iid_fp:
		iid = i.strip("\n")
		#print "iid: %s"%iid

		joelib_fp = file("/home/lwang/proposals/2_MLSMR/joelib/%s.joelib"%iid, "w")
		sdf = "/home/lwang/proposals/2_MLSMR/MLSMR_SDF/%s.sdf"%iid

		rawdata = gen_joelib(sdf)
		print rawdata.keys()
		joelib = []
		for i in joelibcolumns:
			if(rawdata[i[0]]) == "NaN":
				rawdata[i[0]] = '0'
			joelib_fp.write("%s\t%s\n"%(i[1],rawdata[i[0]]))

		joelib_fp.close()
		counter += 1
		print "--------------------%s------------"%counter
		#if counter > 0:
		#	break

	iid_fp.close()
	print "%s compounds processed"%counter
