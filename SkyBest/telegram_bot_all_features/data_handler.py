import json
import os
from datetime import datetime

USER_DATA_FILE = 'users.json'

def save_user_data(user_data, all_users, blocked_users):
    """Save all user data to JSON file"""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump({
            'user_data': {k: {**v, 'start_time': v['start_time'].isoformat() if isinstance(v['start_time'], datetime) else v['start_time'],
                             'last_active': v['last_active'].isoformat() if isinstance(v['last_active'], datetime) else v['last_active'],
                             'subscription_end': v['subscription_end'].isoformat() if v['subscription_end'] and isinstance(v['subscription_end'], datetime) else v['subscription_end']}
                       for k, v in user_data.items()},
            'all_users': list(all_users),
            'blocked_users': list(blocked_users)
        }, f)

def load_user_data():
    """Load user data from JSON file"""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            data = json.load(f)
            user_data = {}
            for k, v in data.get('user_data', {}).items():
                user_data[int(k)] = {
                    **v,
                    'start_time': datetime.fromisoformat(v['start_time']) if v['start_time'] else None,
                    'last_active': datetime.fromisoformat(v['last_active']) if v['last_active'] else None,
                    'subscription_end': datetime.fromisoformat(v['subscription_end']) if v['subscription_end'] else None
                }
            return {
                'user_data': user_data,
                'all_users': set(data.get('all_users', [])),
                'blocked_users': set(data.get('blocked_users', []))
            }
    return {
        'user_data': {},
        'all_users': set(),
        'blocked_users': set()
    }