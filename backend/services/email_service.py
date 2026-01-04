"""
Email service for sending verification codes
Uses Resend API for reliable email delivery
"""
import resend
from config import (
    RESEND_API_KEY,
    MAIL_FROM,
    MAIL_FROM_NAME,
)

# Set Resend API Key
resend.api_key = RESEND_API_KEY


async def send_verification_code(email: str, code: str) -> bool:
    """
    Send verification code to user's email using Resend
    
    Args:
        email: Recipient email address
        code: Verification code to send
        
    Returns:
        True if email sent successfully, False otherwise
        
    Reason:
        - Sends verification code via email using Resend API
        - Uses HTML email template for better formatting
        - Handles errors gracefully
    """
    try:
        # Build HTML email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-bottom: 20px;">Email Verification Code</h2>
                <p style="color: #666; font-size: 16px; margin-bottom: 10px;">Your verification code is:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 8px; margin: 0; padding: 20px; background-color: #f0f8f0; border-radius: 5px; display: inline-block;">
                        {code}
                    </h1>
                </div>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">This code will expire in 10 minutes.</p>
                <p style="color: #999; font-size: 12px; margin-top: 10px;">If you didn't request this code, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">Minecraft Mod Generator</p>
            </div>
        </body>
        </html>
        """
        
        # Send email
        params = {
            "from": f"{MAIL_FROM_NAME} <{MAIL_FROM}>",
            "to": [email],
            "subject": "Email Verification Code - Minecraft Mod Generator",
            "html": html_content,
        }
        
        result = resend.Emails.send(params)
        
        # Resend returns result with id field on success
        # result can be dict or object
        if result:
            email_id = result.get('id') if isinstance(result, dict) else getattr(result, 'id', None)
            if email_id:
                print(f"✅ Email sent successfully to {email}, Resend ID: {email_id}")
                return True
        
        print(f"❌ Failed to send email to {email}, response: {result}")
        return False
            
    except Exception as e:
        print(f"❌ Error sending verification email to {email}: {e}")
        return False

