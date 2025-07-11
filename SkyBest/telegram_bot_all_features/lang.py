
import json
from db import get_lang

langs = {}

def load_languages():
    for lang_code in ['en', 'ru', 'hy', 'fr']:
        with open(f'lang/{lang_code}.json', 'r', encoding='utf-8') as f:
            langs[lang_code] = json.load(f)

def get_text(user_id, key):
    lang = get_lang(user_id)
    return langs.get(lang, langs['en']).get(key, f"[{key}]")
