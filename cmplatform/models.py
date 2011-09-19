from django.db import models
from django.contrib import admin
from simplejson import loads as jsonread
from simplejson import dumps as jsonwrite

class Application(models.Model):
	REGULAR, VIEWER, TESTING = 0, 1, 2
	APPTYPE_CHOICES = (
		(REGULAR, 'Regular'),
		(VIEWER, 'Viewer'),
		(TESTING, 'Testing'),
	)
	name = models.CharField(max_length=250, unique=True)
	url = models.URLField(max_length=1024)
	invoking_url = models.URLField(max_length=1024)
	app_type = models.SmallIntegerField(default=REGULAR,
		choices=APPTYPE_CHOICES)
	owner = models.CharField(max_length=100)
	contact = models.EmailField()
	date_added = models.DateTimeField(auto_now_add=True)
	input_type = models.CharField(max_length=250)
	input_separator = models.CharField(max_length=250, default='\n')
	output_type = models.CharField(max_length=250)

	def __unicode__(self):
		return self.name

	@models.permalink
	def get_absolute_url(self):
		return ('app_details', (), dict(object_id=self.id))

class ApplicationAdmin(admin.ModelAdmin):
	pass

class RunningApplication(models.Model):
	CREATED, INVOKED, RUNNING, FINISHED, FAILED = 0, 1, 2, 3, 4
	STATUS_CHOICES = (
		(CREATED, 'Created'),
		(INVOKED, 'Invoked'),
		(RUNNING, 'Running'),
		(FINISHED, 'Finished'),
		(FAILED, 'Failed'),
	)
	died_status = [FINISHED, FAILED]
	user = models.ForeignKey('auth.User')
	application = models.ForeignKey(Application)
	start_time = models.DateTimeField(auto_now_add=True)
	stop_time = models.DateTimeField(null=True, blank=True)
	status = models.SmallIntegerField(default=CREATED,
										choices=STATUS_CHOICES)
	stdin = models.TextField(blank=True)
	stdout= models.TextField(blank=True)
	token = models.CharField(max_length=36)

	def __unicode__(self):
		return self.application.name
	
	@models.permalink
	def get_absolute_url(self):
		return ("running_app_details", (), dict(object_id=self.id))
	
class RunningApplicationAdmin(admin.ModelAdmin):
	pass

class UserObject(models.Model):
	"""user's storage object, as application input and output"""
	owner = models.ForeignKey('auth.User')
	name = models.CharField(max_length=250)
	value = models.TextField()
	type = models.CharField(max_length=250)
	date_added = models.DateTimeField(auto_now_add=True)
	date_modified = models.DateTimeField(auto_now=True)
	source = models.ForeignKey(RunningApplication, null=True)
	source_class = models.ForeignKey(Application, null=True)

class UserObjectAdmin(admin.ModelAdmin):
	pass

class JSONData(object):
	"""A non-database class to work with json data. Can be used to store pure
	   text as well. Just don't set type to 'json' """
	def __init__(self, text, name=None, type="json"):
		self.name = name or 'Unnamed Object'
		# type of the data. for json input, type will be inferred from within
		# the dictionary data; for non-json input, type must be given explicitly
		if type == 'json':
			data = jsonread(unicode.encode(text, 'utf-8'))
			assert isinstance(data, dict)
			assert "type" in data
			self.type = data['type']
			self.data = data
		else:
			self.type = type
			self.data = text
		self.source = None
		self.source_class = None

	def serialize(self, user):
		uo, created = UserObject.objects.get_or_create(
			owner=user,
			name=self.name)
		uo.type = self.type
		uo.value = self.__str__()
		uo.source = self.source
		uo.source_class = self.source_class
		uo.save()
		return uo

	def __str__(self):
		if self.type == 'text':
			return self.data
		return jsonwrite(self.data)

admin.site.register(Application, ApplicationAdmin)
admin.site.register(RunningApplication, RunningApplicationAdmin)
admin.site.register(UserObject, UserObjectAdmin)
