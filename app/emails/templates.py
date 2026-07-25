from app.core.config import settings


def verification_email_html(token: str, user_name: str | None = None) -> str:
    link = f"{settings.APP_URL}/api/v1/auth/verify-email?token={token}"
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your email</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 0;">
                <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background-color: #0d9488; padding: 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Mizan</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; color: #333333; line-height: 1.6;">{greeting}</p>
                            <p style="font-size: 16px; color: #333333; line-height: 1.6;">Thank you for joining Mizan. Please verify your email address by clicking the button below:</p>
                            <table role="presentation" style="margin: 30px auto;">
                                <tr>
                                    <td align="center" style="border-radius: 4px;">
                                        <a href="{link}" style="display: inline-block; padding: 14px 28px; background-color: #0d9488; color: #ffffff; text-decoration: none; border-radius: 4px; font-weight: bold;">Verify Email Address</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="font-size: 14px; color: #666666; line-height: 1.6;">If you did not create an account, you can safely ignore this email.</p>
                            <p style="font-size: 14px; color: #666666; line-height: 1.6;">This link will expire in 24 hours.</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f4f4f4; padding: 20px 30px; text-align: center;">
                            <p style="font-size: 12px; color: #999999; margin: 0;">Mizan &copy; 2026</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def password_reset_email_html(token: str) -> str:
    link = f"{settings.APP_URL}/reset-password?token={token}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your password</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 0;">
                <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background-color: #0d9488; padding: 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Mizan</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; color: #333333; line-height: 1.6;">Hello,</p>
                            <p style="font-size: 16px; color: #333333; line-height: 1.6;">We received a request to reset your password. Click the button below to choose a new one:</p>
                            <table role="presentation" style="margin: 30px auto;">
                                <tr>
                                    <td align="center" style="border-radius: 4px;">
                                        <a href="{link}" style="display: inline-block; padding: 14px 28px; background-color: #0d9488; color: #ffffff; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="font-size: 14px; color: #666666; line-height: 1.6;">If you did not request a password reset, you can safely ignore this email.</p>
                            <p style="font-size: 14px; color: #666666; line-height: 1.6;">This link will expire in 1 hour.</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f4f4f4; padding: 20px 30px; text-align: center;">
                            <p style="font-size: 12px; color: #999999; margin: 0;">Mizan &copy; 2026</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
