from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if not dictionary:
        return None
    
    # Handle date objects as keys
    if hasattr(key, 'isoformat'):
        # Try to match by date string
        for dict_key in dictionary:
            if hasattr(dict_key, 'isoformat') and dict_key.isoformat() == key.isoformat():
                return dictionary[dict_key]
    
    # Regular dictionary lookup
    return dictionary.get(key)
