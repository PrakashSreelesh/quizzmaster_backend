import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_otp_email(email: str, otp_code: str, verification_url: str):
    """
    Sends an OTP verification email. 
    Falls back to terminal logging if SMTP settings are missing.
    """
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

    # Check if SMTP settings are provided
    smtp_configured = all([
        getattr(settings, "SMTP_HOST", None),
        getattr(settings, "SMTP_PORT", None),
        getattr(settings, "SMTP_USER", None),
        getattr(settings, "SMTP_PASSWORD", None)
    ])

    if not smtp_configured:
        print("\n" + "="*50)
        print(f"SMTP NOT CONFIGURED. LOGGING EMAIL TO TERMINAL:")
        print(f"To: {email}")
        print(f"Subject: {subject}")
        print(f"OTP Code: {otp_code}")
        print(f"Verification URL: {verification_url}")
        print("="*50 + "\n")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"FAILED TO SEND EMAIL: {e}")
        # Even if it fails, we logged it to terminal if needed or just log it here
        print(f"FALLBACK OTP LOG: {email} -> {otp_code}")


def send_password_reset_email(email: str, otp_code: str):
    """
    Sends an OTP for password reset.
    """
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

    smtp_configured = all([
        getattr(settings, "SMTP_HOST", None),
        getattr(settings, "SMTP_PORT", None),
        getattr(settings, "SMTP_USER", None),
        getattr(settings, "SMTP_PASSWORD", None)
    ])

    if not smtp_configured:
        print("\n" + "="*50)
        print(f"SMTP NOT CONFIGURED. LOGGING PASSWORD RESET OTP TO TERMINAL:")
        print(f"To: {email}")
        print(f"Subject: {subject}")
        print(f"OTP Code: {otp_code}")
        print("="*50 + "\n")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"FAILED TO SEND PASSWORD RESET EMAIL: {e}")
        print(f"FALLBACK OTP LOG: {email} -> {otp_code}")
