"""use this script to manually add screen upload permission to some users"""
from django.contrib.auth.models import User, Permission
p = Permission.objects.get(codename="add_screen")
def grant(u):
u = User.objects.get(email=u)
  if not u.has_perm('screendb.add_screen'):
    u.user_permissions.add(p)

