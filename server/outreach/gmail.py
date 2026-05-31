import smtplib
from email.mime.text import MIMEText
from server.config import settings


def send_gmail(to_address: str, message: str) -> bool:
    msg = MIMEText(message)
    msg["Subject"] = "Following up"
    msg["From"] = settings.gmail_address
    msg["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.gmail_address, settings.gmail_app_password)
        smtp.send_message(msg)
    return True
