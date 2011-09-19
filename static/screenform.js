var libs;
var lib_select_ctrl;
var aurl = '/compounds/_ajax';// WARNING: hardcoded URL
var id_input = '';
function ui()
{
	// make textarea small and auto-expand on click if empty
	$("textarea").each(function() {
		if (! $(this).text()) {
			$(this).css('height', '1em').css('width', '5em').focus(function() {
				if (! $(this).data('sized')) {
					$(this).data('sized', true);
					$(this).css('height', '5em').css('width', '90%');
				}
			});
		}
	});
	// load library selection widget
	$.get(aurl, function(data) {
		libs = data;
		lib_select_ctrl = '<select><option>None</option>';
		for (var i = 0; i < libs.length; i ++)
			lib_select_ctrl += '<option>' + libs[i] + '</options>';
		lib_select_ctrl += '</select>';
		$("a.id_compound_show").parent().find("span span.select").html(lib_select_ctrl);
	});
	// replace compound input box with more friendly widgets
	$("input#id_compound").hide().after('<a class="id_compound_show" href="#">None. Click to set</a><span style="display:none"><span class="select"></span><input type="text" size="10"/><button class="id_check" style="float:none">OK</button><button class="id_cancel" style="float:none">Cancel</button></span>');
	$("a.id_compound_show").live('click', function() {
		$(this).parent().find("span").show();
		$(this).hide();
		return false;
	});
	$("button.id_cancel").live('click', function() {
		$(this).parent().parent().find('a.id_compound_show').show();
		$(this).parent().hide();
		return false;
	});
	$("button.id_check").live('click', function() {
		var lib = $(this).parent().find('select').get(0).value;
		if (lib == 'None') {
			$(this).parent().parent().find('input#id_compound').get(0).value = '';
			$(this).parent().parent().find('a.id_compound_show').text('None. Click to set').show();
			$(this).parent().hide();
		} else {
			var cid = $(this).parent().find('input[type=text]').get(0).value;
			var url = aurl + '?request=id_check&lib=' + escape(lib) + '&cid=' + escape(cid);
			var btn = $(this);
			$.get(url, function(data) {
				if (data.id < 0) 
					alert('Compound not found in the database!');
				else {
					btn.parent().parent().find('input#id_compound').get(0).value = data.id;
					btn.parent().parent().find('a.id_compound_show').text(lib + ' ' + cid).show();
					btn.parent().hide();
				}
			});
		}
		return false;
	});
	// if already a value is given (in forms rejected by validation)
	$("input#id_compound").each(function() {
		var iid = $(this).get(0).value;
		if (iid) {
			var url = aurl + '?request=reverse_id_check&id=' + iid;
			var self = $(this);
			$(this).parent().find('a.id_compound_show').text('Loading...');
			setTimeout(function() {
			$.get(url, function(data) {
				if (data.lib) {
					$(self).parent().find('select').get(0).value = data.lib;
					$(self).parent().find('span input').get(0).value = data.cid;
					$(self).parent().find('a.id_compound_show').text(data.lib + " " + data.cid);
				} else {
					$(self).get(0).value = '';
				}
			});}, 1000);
		}
	});
	
	// publication input modes
	var modes_line = $("label[for=id_mode]").parent().parent();
	$("label[for=id_mode]").parent().remove();
	modes_line.find('td').attr('colspan', '2');
	modes_line.find('option:nth-child(1)').text('Select an input method:')
	for (var i = 2; i < 5; i ++)
		modes_line.find('option:nth-child(' + i + ')').text('  through ' + modes_line.find('option:nth-child(' + i + ')').text());
	lines = modes_line.nextAll();
	lines.hide();
	modes_line.find('select').change(function() {
		lines.hide();
		if ($(this).get(0).value == 'pubmed') {
			$(lines[0]).fadeIn('slow');
		} else if ($(this).get(0).value == 'publication') {
			lines.slice(1,7).fadeIn('slow');
		} else if ($(this).get(0).value == 'web') {
			$(lines[7]).fadeIn('slow');
		}
	});
	modes_line.find('select').trigger('change');
	
	// standard annotation: assay 2 & 3 are optional, so hide them
	$("input[value=Standard Compound Annotation]").parent().find('tr:nth-child(4n+9)').before('<tr class="next-assay"><th colspan="2"><a href="#" class="button add-assay">Add one more assay</a><a href="#" class="button remove-assay" style="display:none">Remove the following assay</a></th></tr>');
	$("input[value=Standard Compound Annotation]").parent().find('tr:nth-child(9)').nextAll().each(function() {
		$(this).hide();
	});
	$("a.add-assay").live('click', function() {
		$(this).parent().parent().nextUntil("tr.next-assay").show();
		var n = $(this).parent().parent().nextAll("tr.next-assay");
		if (n.length) $(n[0]).show();
		$(this).hide().next().show();
		return false;
	});
	$("a.remove-assay").live('click', function() {
		$(this).parent().parent().nextUntil("tr.next-assay").each(function() {
			$(this).find('input, textarea, select').each(function() {$(this).get(0).value='';});
		}).hide();
		$(this).hide().prev().show();
		return false;
	});
	// deal with validation rejected bounded form
	var assay2 = assay3 = false;
	$("input[value=Standard Compound Annotation]").parent().find('input, textarea, select').each(function() {
		if ($(this).get(0).value.length) {
			if ($(this).attr('name').match(/^a2_/)) assay2 = true;
			if ($(this).attr('name').match(/^a3_/)) assay3 = true;
		}
	});
	if (assay2) 
		$("input[value=Standard Compound Annotation]").parent().find('tr:nth-child(9)').find("a.add-assay").trigger('click');
	if (assay3) 
		$("input[value=Standard Compound Annotation]").parent().find('tr:nth-child(14)').find("a.add-assay").trigger('click');
}

$(document).ready(function() {
	ui();
	// ajaxize the form submission
	var active_form = null;
	if ($(".file-upload-box form").ajaxForm) {
		var options = {
			data : {'ajax':'1'},
			dataType : 'json',
			beforeSubmit : function(arr, form, options) {
				active_form = form;
				form.find('table').find('input, select, textarea').attr('readonly', true);
				form.find('input[type=submit]').attr('disabled', true).val('working');
			},
			success: function(data) {
				if (data.form) {
					$(active_form).find('table').html(data.form);
					ui();
					$(active_form).find('table').css('opacity', 0.2).fadeTo(1000, 1)
					$(active_form).find('input[type=submit]').removeAttr('disabled').val('Submit');
				}
				
				if (data.file) {
					if ($("#file-block").length) {
						if (data.has_compound)
							$(data.file).appendTo($("#file-block")).css('opacity', 0.2).fadeTo(500, 1).fadeTo(500,0.2).fadeTo(500,1).fadeTo(500,0.2).fadeTo(500,1);
						else
							$.scrollTo($(data.file).appendTo($("#screen-file-block")).css('opacity', 0.2).fadeTo(500, 1).fadeTo(500,0.2).fadeTo(500,1).fadeTo(500,0.2).fadeTo(500,1), 1000, {offset:{left:0, top:-300}});

					} else
						alert("file upload succeeded");
				} 
				
				if (data.error){
					alert(data.error);
				}
			},
		};
		$(".file-upload-box form").ajaxForm(options);
	}
});