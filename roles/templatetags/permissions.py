from django import template
from django.contrib.auth.models import Permission

register = template.Library()

@register.filter
def has_perm(user, perm_name):
    has_permission = user.has_perm(perm_name)
    return has_permission

@register.filter
def get_permission_status(role, perm_codename):
    """
    Check if a role has a specific permission and return 'Yes' or 'No'
    Usage: {{ role|get_permission_status:'add_course' }}
    """
    try:
        # Build the full permission codename
        if not perm_codename.startswith('add_') and not perm_codename.startswith('view_') and not perm_codename.startswith('change_') and not perm_codename.startswith('delete_'):
            full_codename = f'{perm_codename}'
        else:
            full_codename = perm_codename
            
        # Check if role has this permission
        has_permission = role.permissions.filter(codename=full_codename).exists()
        return 'Yes' if has_permission else 'No'
    except:
        return 'No'
