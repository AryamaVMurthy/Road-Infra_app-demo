import random
from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=True,
)


class EmailService:
    @staticmethod
    async def send_otp(email: str, otp: str):
        if settings.DEV_MODE:
            print(f"[DEV MODE] Skipping email send. OTP for {email}: {otp}")
            return True

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd;">
                    <h2 style="color: #2563eb; text-align: center;">MARG Authentication</h2>
                    <p>Hello,</p>
                    <p>Your One-Time Password (OTP) for accessing the Monitoring Application for Road Governance (MARG) is:</p>
                    <div style="background-color: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #1f2937; margin: 20px 0;">
                        {otp}
                    </div>
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    <p>If you did not request this code, please ignore this email.</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                        &copy; {datetime.now().year} MARG Platform. All rights reserved.
                    </p>
                </div>
            </body>
        </html>
        """

        message = MessageSchema(
            subject="MARG - Your Authentication Code",
            recipients=[email],
            body=html_content,
            subtype=MessageType.html,
        )

        fm = FastMail(conf)
        try:
            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"Email failed to send: {e}")
            print(f"FALLBACK OTP for {email}: {otp}")
            return False

    @staticmethod
    def generate_otp() -> str:
        return str(random.randint(100000, 999999))
