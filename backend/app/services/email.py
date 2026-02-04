import random
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from pydantic import EmailStr

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
)


class EmailService:
    @staticmethod
    async def send_otp(email: EmailStr, otp: str):
        # In development mode, skip actual email sending to avoid SMTP timeout
        if settings.DEV_MODE:
            print(f"[DEV MODE] Skipping email send. OTP for {email}: {otp}")
            return True

        message = MessageSchema(
            subject="MARG - Your OTP",
            recipients=[email],
            body=f"Your OTP code is: {otp}. It expires in 10 minutes.",
            subtype="plain",
        )
        fm = FastMail(conf)
        try:
            # In a real environment with credentials, this would send.
            # We wrap it to ensure it doesn't crash the prototype if credentials are fake.
            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"Email failed to send: {e}")
            print(f"DEVELOPMENT OTP for {email}: {otp}")
            return False

    @staticmethod
    def generate_otp() -> str:
        return str(random.randint(100000, 999999))
