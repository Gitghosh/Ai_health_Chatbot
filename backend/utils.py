from backend.templates import TEMPLATES

def get_message(key: str, lang: str = "en", **kwargs) -> str:
    """Fetch a message template in the given language, with optional placeholders."""
    template = TEMPLATES.get(key, TEMPLATES["default"])
    text = template.get(lang, template["en"])  # fallback to English
    return text.format(**kwargs)