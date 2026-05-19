import smtplib
from email.message import EmailMessage

SMTP_HOST = "172.16.10.115"
SMTP_PORT = 25
FROM_EMAIL = "app-mailer1@dswd.gov.ph"

def send_verification_email(to_email: str, token: str):
    verify_link = f"https://pantawid-ods-staging.dswd.gov.ph/auth/verify-email?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Verify your email"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(
        f"Dear User,\n\n"
        f"Please verify your email address by clicking the link below:\n\n"
        f"{verify_link}\n\n"
        f"If you did not request this verification, please ignore this message.\n\n"
        f"Thank you,\n"
        f"DSWD Pantawid ODS Team"
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()  # optional but recommended
            # server.login(...)  # uncomment only if authentication is required
            server.send_message(msg)
        print(f"✅ Verification email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")