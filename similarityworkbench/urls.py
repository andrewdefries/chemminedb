from django.conf.urls.defaults import *
urlpatterns = patterns('',
	url(r'^(?P<sid>([0-9a-z]{32})?)$', 'similarityworkbench.views.ui', name="similarity-workbench-ui"),
)
