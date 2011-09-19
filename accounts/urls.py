from django.conf.urls.defaults import *
from views import cm_login, cm_logout

urlpatterns = patterns('',
	url(r'^login/$',  cm_login, dict(), name="login"),
    url(r'^logout/$', cm_logout, dict(), name="logout"),
    url(r'^password/$', 'django.contrib.auth.views.password_change', name="change_password"),
    url(r'^password/done/$', 'django.contrib.auth.views.password_change_done'),
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset'),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
    url(r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
	url(r'',  cm_login),
)
