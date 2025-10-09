"""
Field mapping configuration for Google Sheets
Defines column names and their positions
"""

# Google Sheets column mapping
# Adjust these according to your actual sheet structure

# Order sheet columns
ORDER_FIELDS = {
    'order_id': 'A',
    'user_id': 'B',
    'username': 'C',
    'timestamp': 'D',
    'items': 'E',
    'total': 'F',
    'status': 'G',
    'phone': 'H',
    'address': 'I',
    'notes': 'J'
}

# Menu/Product sheet columns
MENU_FIELDS = {
    'id': 'A',
    'name': 'B',
    'description': 'C',
    'price': 'D',
    'category': 'E',
    'available': 'F',
    'image_url': 'G'
}

# User data columns (if needed)
USER_FIELDS = {
    'user_id': 'A',
    'username': 'B',
    'phone': 'C',
    'address': 'D',
    'registered': 'E'
}

# Sheet names
SHEET_NAMES = {
    'orders': 'Orders',
    'menu': 'Menu',
    'users': 'Users'
}

# Field validation
REQUIRED_ORDER_FIELDS = ['user_id', 'timestamp', 'items', 'total']
REQUIRED_MENU_FIELDS = ['name', 'price']

def get_column_letter(field_name, field_type='order'):
    """
    Get column letter for a field name
    
    Args:
        field_name: Name of the field
        field_type: Type of field mapping ('order', 'menu', 'user')
    
    Returns:
        Column letter (e.g., 'A', 'B', 'C')
    """
    mapping = {
        'order': ORDER_FIELDS,
        'menu': MENU_FIELDS,
        'user': USER_FIELDS
    }
    
    return mapping.get(field_type, {}).get(field_name, 'A')

def get_sheet_name(sheet_type):
    """Get sheet name by type"""
    return SHEET_NAMES.get(sheet_type, 'Sheet1')