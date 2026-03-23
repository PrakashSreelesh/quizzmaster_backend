import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger("quizzmaster")


def _send_email(to_email: str, subject: str, html_content: str):
    """
    Core email sender. Uses SMTP_SSL (port 465) for Render compatibility.
    Falls back to STARTTLS (port 587) if SMTP_SSL fails.
    """
    smtp_configured = all([
        getattr(settings, "SMTP_HOST", None),
        getattr(settings, "SMTP_PORT", None),
        getattr(settings, "SMTP_USER", None),
        getattr(settings, "SMTP_PASSWORD", None),
    ])

    if not smtp_configured:
        logger.warning("SMTP NOT CONFIGURED. Email not sent to: %s | Subject: %s", to_email, subject)
        return

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    # Try SMTP_SSL on port 465 first (works on Render)
    try:
        logger.info("SMTP: Trying SMTP_SSL — host=%s port=465 user=%s", settings.SMTP_HOST, settings.SMTP_USER)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, 465, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("SMTP: Email sent successfully via SMTP_SSL (port 465) to %s", to_email)
        return
    except Exception as e:
        logger.error("SMTP: SMTP_SSL (port 465) failed: %s", e)

    # Fallback: STARTTLS on port 587
    try:
        logger.info("SMTP: Trying STARTTLS — host=%s port=587", settings.SMTP_HOST)
        with smtplib.SMTP(settings.SMTP_HOST, 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("SMTP: Email sent successfully via STARTTLS (port 587) to %s", to_email)
        return
    except Exception as e:
        logger.error("SMTP: STARTTLS (port 587) failed: %s", e)
        raise


def send_otp_email(email: str, otp_code: str, verification_url: str):
    """Sends an OTP verification email."""
    subject = "Verify your QuizzMaster account"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px; text-align: center;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #1e293b; padding: 30px; border-radius: 20px; border: 1px solid #334155;">
                <h1 style="color: #8b5cf6;">QuizzMaster</h1>
                <p style="font-size: 16px; color: #94a3b8;">Welcome! Please use the code below to verify your account.</p>
                <div style="font-size: 32px; font-weight: bold; background-color: #0f172a; padding: 20px; border-radius: 12px; margin: 30px 0; color: #fff; letter-spacing: 5px;">
                    {otp_code}
                </div>
                <p style="font-size: 14px; color: #64748b;">This code expires in 20 minutes.</p>
                <a href="{verification_url}" style="display: inline-block; background-color: #8b5cf6; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 20px;">
                    Verify Account
                </a>
                <hr style="border: 0; border-top: 1px solid #334155; margin: 30px 0;">
                <p style="font-size: 12px; color: #475569;">If you didn't request this, you can safely ignore this email.</p>
            </div>
        </body>
    </html>
    """
    try:
        _send_email(email, subject, html_content)
    except Exception as e:
        logger.error("FAILED TO SEND OTP EMAIL to %s: %s", email, e)
        logger.info("FALLBACK OTP LOG: %s -> %s", email, otp_code)


def send_password_reset_email(email: str, otp_code: str):
    """Sends an OTP for password reset."""
    subject = "Reset your QuizzMaster password"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px; text-align: center;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #1e293b; padding: 30px; border-radius: 20px; border: 1px solid #334155;">
                <h1 style="color: #f43f5e;">QuizzMaster</h1>
                <p style="font-size: 16px; color: #94a3b8;">You requested a password reset. Use the code below to reset your password.</p>
                <div style="font-size: 32px; font-weight: bold; background-color: #0f172a; padding: 20px; border-radius: 12px; margin: 30px 0; color: #fff; letter-spacing: 5px;">
                    {otp_code}
                </div>
                <p style="font-size: 14px; color: #64748b;">This code expires in 20 minutes.</p>
                <p style="text-align: left; margin-top: 30px; color: #94a3b8; font-size: 13px;">
                    Steps:
                    <ol style="text-align: left;">
                        <li>Open the Reset Password page.</li>
                        <li>Enter this code.</li>
                        <li>Choose a new secure password.</li>
                    </ol>
                </p>
                <hr style="border: 0; border-top: 1px solid #334155; margin: 30px 0;">
                <p style="font-size: 12px; color: #475569;">If you didn't request this, please change your password immediately.</p>
            </div>
        </body>
    </html>
    """
    try:
        _send_email(email, subject, html_content)
    except Exception as e:
        logger.error("FAILED TO SEND PASSWORD RESET EMAIL to %s: %s", email, e)
        logger.info("FALLBACK OTP LOG: %s -> %s", email, otp_code)