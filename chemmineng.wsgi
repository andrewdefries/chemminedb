import os
import sys
sys.path.append('/srv')
sys.path.append('/srv/chemmineng')

os.environ['DJANGO_SETTINGS_MODULE'] = 'chemmineng.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
