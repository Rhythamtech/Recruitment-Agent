import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

context = ssl.create_default_context()
smtp_server = os.getenv("SMTP_HOST")
port = os.getenv("SMTP_PORT")

sender_mail =  os.getenv("SMTP_EMAIL")
sender_password = os.getenv("SMTP_PASSWORD")


def send(subject: str, receiver_mail: str, html_content: str):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_mail
    msg['To'] = receiver_mail
    msg.add_alternative(html_content, subtype='html')

    try:
        print("Connecting to server...")
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_mail, sender_password)
            server.send_message(msg)
            print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")