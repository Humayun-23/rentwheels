import os
import sys
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

smtp_host = os.getenv("SMTP_HOST")
smtp_port = int(os.getenv("SMTP_PORT", "587"))
smtp_user = os.getenv("SMTP_USER")
smtp_password = os.getenv("SMTP_PASSWORD")
smtp_sender = os.getenv("SMTP_SENDER", smtp_user or "noreply@gopanda.in")
to_email = os.getenv("MAIL_TO", "test@example.com")

if not smtp_host or not smtp_user or not smtp_password:
    sys.exit("Missing SMTP_HOST/SMTP_USER/SMTP_PASSWORD in env")

msg = EmailMessage()
msg["Subject"] = "Mailtrap live SMTP test"
msg["From"] = smtp_sender
msg["To"] = to_email
msg.set_content("Congrats for sending a live SMTP email with Mailtrap!")

if smtp_port == 465:
    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
else:
    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
    server.starttls()

with server:
    server.login(smtp_user, smtp_password)
    server.send_message(msg)

print("Sent")