import MySQLdb, sys
import pyjson

host = "bioweb"
user = "ycao"
db = "ptdb"

con = MySQLdb.connect(host=host, user=user, db=db)
cur = con.cursor()


if __name__ == "__main__":


	screenid = int(sys.argv[1])

	# decide keys
	query = """SELECT name, type, col_id FROM screen_obj_schema WHERE screenid=%s and function='key'"""%screenid
	cur.execute(query)
	key_name, key_type, key_col = cur.fetchone()[0:3]

	tbl_name = "screen_obj_%s"%key_type

	# decide name key
	query = """SELECT col_id, name FROM screen_obj_schema WHERE screenid=%s and function='name key'"""%screenid
	cur.execute(query)
	name_key_col, name_key = cur.fetchone()[0:2]

	# decide SALK ID
	query = """SELECT col_id, name FROM screen_obj_schema WHERE screenid=%s and function='salk'"""%screenid
	cur.execute(query)
	salk_col, salk_name = cur.fetchone()[0:2]
	
	# get all distinct Comparison Set IDs
	sets = []
	query = """SELECT distinct value FROM %s WHERE col_id=%s"""%(tbl_name, key_col)
	cur.execute(query)
	for i in cur.fetchall():
		sets.append(i[0])
	
	# get all treamtments = {col_id:name}
	trm = {} 
	query = """SELECT name, col_id FROM screen_obj_schema WHERE screenid=%s and function='treatment'"""%screenid
	cur.execute(query)
	for i in cur.fetchall():
		trm[i[1]] = i[0]

	# get mean values
	all = {}

	# for every comparison set
	for set_id in sets:

		print set_id

		set = {}
		wt = {}
		organism = {}
		ati = ''
		salk_id = ''

		# get AT#
		query = """SELECT distinct(value) FROM screen_obj_string WHERE screenid=%s and col_id=%s and set_id=%s and value != 'wt'"""%(screenid, name_key_col, set_id)
		cur.execute(query)
		result = cur.fetchall()
		if len(result) > 1:
			print "Set %s has %s organisms."%(set_id,len(result))
		else:
			ati = i[0]
		#for i in cur.fetchall():
		#	if i[0]!='wt':
		#		ati = i[0]
		#		break

		# get and SALK_ID
		query = """SELECT distinct(value) FROM screen_obj_string WHERE screenid=%s and col_id=%s and set_id=%s"""%(screenid, salk_col, set_id)
		cur.execute(query)
		result = cur.fetchall()
		for i in result:
			if len(i[0]) != 0:
				salk_id = i[0]
				break

		for treatment in trm.keys():

			# mean value for wt
			query = """SELECT sum(value)/count(value) FROM screen_obj_double WHERE screenid=%s and col_id=%s and set_id=%s and wt=1"""%(screenid, treatment, set_id)
			cur.execute(query)
			mean = cur.fetchone()[0]
			wt[trm[treatment]] = "%s"%mean 

			# mean value for organism
			query = """SELECT sum(value)/count(value) FROM screen_obj_double WHERE screenid=%s and col_id=%s and set_id=%s and wt=0"""%(screenid, treatment, set_id)
			cur.execute(query)
			mean = cur.fetchone()[0]
			organism[trm[treatment]] = "%s"%mean 

		set["wt"] = wt
		set["organism"] = organism
		set["At#"] = ati
		set["salk"] = salk_id
		all["%s"%set_id] = set

		#if set_id == 497:
		#	print set
	#print all

	sys.exit(0)


	###################

	all_js = pyjson.write(all)
	#print all_js

	tmpl = """

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
 <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Plot Generating Test</title>
    <link href="layout.css" rel="stylesheet" type="text/css"></link>
    <!--[if IE]><script language="javascript" type="text/javascript" src="excanvas.pack.js"></script><![endif]-->
    <script language="javascript" type="text/javascript" src="jquery.js"></script>
    <script language="javascript" type="text/javascript" src="jquery.flot.js"></script>
 </head>
    <body>
    <h1>Plot generating test1 </h1>



<script id="source" language="javascript" type="text/javascript">

var all;
$(function () {
    var d1 = [];
    for (var i = 0; i < 14; i += 0.5)
        d1.push([i, Math.sin(i)]);

	all = %s;

    var wt = "";
    var organism = "";

	var counter = 0;
	for(i in all)
	{
		wt_d1 = all[i]['wt']['MS'];
		wt_d2 = all[i]['wt']['Heat'];
		wt_d3 = all[i]['wt']['Cold'];
		wt_d4 = all[i]['wt']['Oxdative'];

		d1 = all[i]['organism']['MS'];
		d2 = all[i]['organism']['Heat'];
		d3 = all[i]['organism']['Cold'];
		d4 = all[i]['organism']['Oxdative'];

	
		wt = [[0, wt_d1], [3, wt_d2],[6, wt_d3], [9, wt_d4]];
		organism = [[1, d1], [4, d2],[7, d3], [10, d4]];
		
	    $.plot($(".placeholder:eq("+counter+")"), [
	        {
	            data: wt,
	            bars: { show: true }
			},
			{
	            data: organism,
	            bars: { show: true }
	        }
	       
	    ]);

		counter += 1;

	
	};

    
});
</script>

	__DIV__TMPL__
 </body>
</html>
"""%all_js

	div_tmpl = """
    <div class="placeholder" style="width:600px;height:300px"></div>
"""

	fp = open("/home/lwang/.html/plot_tmpl.html","w")
	divs = ""
	for i in range(len(all)):
		divs += div_tmpl
	tmpl = tmpl.replace("__DIV__TMPL__", divs)
	fp.write(tmpl)
	fp.close()

