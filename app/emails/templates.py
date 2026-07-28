from app.core.config import settings
from app.emails.base import (
    BRAND_EMERALD,
    BRAND_INK,
    BRAND_LINE,
    BRAND_MUTED,
    BRAND_SUBTLE,
    FONT_BODY,
    _body_close,
    _body_open,
    card_close,
    card_open,
    _doctype,
    _head,
    _html_close,
    _html_open,
    cta_button,
    expiry_notice,
    footer_section,
    header_section,
    safety_notice,
)


def _wraps(title: str, inner: str, expiry_text: str) -> str:
    return "".join([
        _doctype(),
        _html_open(),
        _head(title),
        _body_open(),
        header_section(),
        card_open(padding_top="36px", padding_bottom="36px"),
        inner,
        card_close(),
        footer_section(),
        _body_close(),
        _html_close(),
    ])


# ─────────────────────────────────────────────────────────────
# VERIFICATION EMAIL
# ─────────────────────────────────────────────────────────────

def verification_email_html(token: str, user_name: str | None = None) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"

    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            <p style="
                font-family: {FONT_BODY};
                font-size: 16px;
                font-weight: 400;
                color: {BRAND_MUTED};
                margin: 0 0 8px;
                line-height: 1.65;
            ">Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,</p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 16px;
                font-weight: 400;
                color: {BRAND_MUTED};
                margin: 0 0 6px;
                line-height: 1.65;
            ">So glad you're here.</p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 16px;
                font-weight: 400;
                color: {BRAND_MUTED};
                margin: 0 0 32px;
                line-height: 1.65;
            ">Mizan is a quiet space to grow your spiritual life, one small act of goodness at a time. To keep your account safe and yours alone, please verify your email with the code below:</p>
        </td>
    </tr>
</table>"""

    below_cta = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            <p style="
                font-family: {FONT_BODY};
                font-size: 13px;
                color: {BRAND_SUBTLE};
                margin: 28px 0 20px;
                line-height: 1.65;
            ">Your six-digit verification code:</p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 8px;
                color: {BRAND_EMERALD};
                word-break: break-all;
                margin: 0;
                background-color: #F7F3EC;
                padding: 10px 14px;
                border-radius: 8px;
                border: 1px solid {BRAND_LINE};
            ">{token}</p>
        </td>
    </tr>
</table>"""

    post = f"""{below_cta}
{safety_notice()}
{expiry_notice("This link expires in <strong>24 hours</strong> for your security.")}"""

    title = "Welcome to Mizan — Verify your email"

    return _wraps(title, body + post, "This code expires in 24 hours for your security.")


# ─────────────────────────────────────────────────────────────
# PASSWORD RESET EMAIL
# ─────────────────────────────────────────────────────────────

def password_reset_email_html(token: str) -> str:
    link = f"{settings.APP_URL}/reset-password?token={token}"
    
    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            <p style="
                font-family: {FONT_BODY};
                font-size: 16px;
                font-weight: 400;
                color: {BRAND_MUTED};
                margin: 0 0 8px;
                line-height: 1.65;
            ">Assalamu alaikum,</p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 16px;
                font-weight: 400;
                color: {BRAND_MUTED};
                margin: 0 0 6px;
                line-height: 1.65;
            ">We received a request to reset your Mizan account password.</p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 16px;
                font-weight: 400;
                color: {BRAND_MUTED};
                margin: 0 0 32px;
                line-height: 1.65;
            ">Choose a new password below:</p>
        </td>
    </tr>
</table>"""

    cta = cta_button(link, "Reset password")
    
    below_cta = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            <p style="
                font-family: {FONT_BODY};
                font-size: 13px;
                color: {BRAND_SUBTLE};
                margin: 28px 0 20px;
                line-height: 1.65;
            ">Or copy and paste this link into your browser:</p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 12px;
                color: {BRAND_EMERALD};
                word-break: break-all;
                margin: 0;
                background-color: #F7F3EC;
                padding: 10px 14px;
                border-radius: 8px;
                border: 1px solid {BRAND_LINE};
            ">{link}</p>
        </td>
    </tr>
</table>"""

    post = f"""{below_cta}
{safety_notice()}
{expiry_notice("This link expires in <strong>1 hour</strong> for your security.")}"""

    title = "Reset your password — Mizan"
    
    return _wraps(title, body + cta + post, "This link expires in 1 hour for your security.")
