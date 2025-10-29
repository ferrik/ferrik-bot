"""🔄 User States"""

STATES = {
    'idle': 'На головному меню',
    'awaiting_phone': 'Чекає телефон',
    'awaiting_address': 'Чекає адресу',
}

def get_user_state(user_id):
    # ... логіка станів

def set_user_state(user_id, state):
    # ... логіка установки стану
