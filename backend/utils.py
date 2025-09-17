# from backend.templates import TEMPLATES

# def get_message(key: str, lang: str = "en", **kwargs) -> str:
#     """Fetch a message template in the given language, with optional placeholders."""
#     template = TEMPLATES.get(key, TEMPLATES["default"])
#     text = template.get(lang, template["en"])  # fallback to English
#     return text.format(**kwargs)


# backend/utils.py
import os
from twilio.rest import Client
from backend.templates import TEMPLATES

# ---------------------------
# Message Template Function (Your existing code)
# ---------------------------
def get_message(key: str, lang: str = "en", **kwargs) -> str:
    """Fetch a message template in the given language, with optional placeholders."""
    template = TEMPLATES.get(key, TEMPLATES["default"])
    text = template.get(lang, template["en"])  # fallback to English
    return text.format(**kwargs)


# ---------------------------
# Twilio WhatsApp Sending Function (New code)
# ---------------------------
def send_whatsapp_message(to_number: str, message: str):
    """Sends a WhatsApp message using Twilio credentials from environment variables."""
    # Fetch credentials from environment variables
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    # Check if all credentials are set
    if not all([account_sid, auth_token, twilio_number]):
        print("ERROR: Twilio environment variables are not fully configured.")
        return False

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            from_=twilio_number,
            body=message,
            to=f"whatsapp:{to_number}"
        )
        print(f"WhatsApp notification sent successfully to {to_number}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send Twilio message: {e}")
        return False