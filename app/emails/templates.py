from app.core.config import settings
from app.emails.base import (
    BRAND_EMERALD,
    BRAND_INK,
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

# NOTE: your Flutter theme is bronze (kBronze = #8B6842), but base.py's
# BRAND_EMERALD is what these templates lean on for the code box / accent
# color. That was a mismatch: the email read "green brand", app
# reads "bronze brand". Swap BRAND_EMERALD -> a bronze token in base.py
# (e.g. BRAND_BRONZE = "#8B6842") and these templates will match the app
# with zero further changes here. Until then I've kept the import name so
# this drops in without touching base.py, per your ask.

BRAND_ACCENT = BRAND_EMERALD
BRAND_CODE_BG = "#F7F0E7"  # kIvory
BRAND_CODE_BORDER = "#E8DDD1"  # kLine


def _wraps(title: str, inner: str, expiry_text: str) -> str:
    return "".join(
        [
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
        ]
    )


def _p(
    text: str,
    *,
    size: int = 16,
    weight: int = 400,
    color: str = BRAND_MUTED,
    margin: str = "0 0 6px",
    line_height: float = 1.65,
) -> str:
    return f"""<p style="
        font-family: {FONT_BODY};
        font-size: {size}px;
        font-weight: {weight};
        color: {color};
        margin: {margin};
        line-height: {line_height};
    ">{text}</p>"""


# ─────────────────────────────────────────────────────────────
# VERIFICATION EMAIL
# ─────────────────────────────────────────────────────────────


def _legacy_verification_email_html(token: str, user_name: str | None = None) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"

    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {
        _p(
            f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,',
            margin="0 0 8px",
        )
    }
            {_p("We're really glad you're here.", margin="0 0 6px")}
            {
        _p(
            "Mizan is a quiet space to grow your spiritual life, one small act "
            "of goodness at a time, and we'd love for it to be yours alone. "
            "Enter the code below to verify it's really you:",
            margin="0 0 28px",
        )
    }
        </td>
    </tr>
</table>"""

    below_cta = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            {_p("Your verification code", size=13, color=BRAND_SUBTLE, margin="28px 0 14px")}
            <p style="
                font-family: {FONT_BODY};
                font-size: 32px;
                font-weight: 700;
                letter-spacing: 10px;
                color: {BRAND_ACCENT};
                word-break: break-all;
                margin: 0;
                background-color: {BRAND_CODE_BG};
                padding: 16px 20px;
                border-radius: 12px;
                border: 1px solid {BRAND_CODE_BORDER};
                text-align: center;
            ">{token}</p>
            {_p("Didn't request this? You can safely ignore this email.", size=13, color=BRAND_SUBTLE, margin="18px 0 0")}
        </td>
    </tr>
</table>"""

    post = f"""{below_cta}
{safety_notice()}
{expiry_notice("This code expires in <strong>24 hours</strong> for your security.")}"""

    title = "Welcome to Mizan, verify your email"

    return _wraps(
        title, body + post, "This code expires in 24 hours for your security."
    )


def _legacy_email_change_request_html(
    token: str, user_name: str | None = None, new_email: str = ""
) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"

    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("You requested to change the email address on your Mizan account.", margin="0 0 6px")}
            {_p(f"New email: <strong>{new_email}</strong>", margin="0 0 6px")}
            {_p("Enter the code below to verify your new address:", margin="0 0 28px")}
        </td>
    </tr>
</table>"""

    below_cta = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            {_p("Your verification code", size=13, color=BRAND_SUBTLE, margin="28px 0 14px")}
            <p style="
                font-family: {FONT_BODY};
                font-size: 32px;
                font-weight: 700;
                letter-spacing: 10px;
                color: {BRAND_ACCENT};
                word-break: break-all;
                margin: 0;
                background-color: {BRAND_CODE_BG};
                padding: 16px 20px;
                border-radius: 12px;
                border: 1px solid {BRAND_CODE_BORDER};
                text-align: center;
            ">{token}</p>
            {_p("This code expires in 24 hours.", size=13, color=BRAND_SUBTLE, margin="18px 0 0")}
            {_p("If you did not request this change, you can safely ignore this email. Your account remains secure.", size=13, color=BRAND_SUBTLE, margin="6px 0 0")}
        </td>
    </tr>
</table>"""

    post = f"""{below_cta}
{safety_notice()}
{expiry_notice("This code expires in 24 hours for your security.")}"""

    title = "Verify your new Mizan email"

    return _wraps(
        title, body + post, "This code expires in 24 hours for your security."
    )


def _legacy_email_change_notification_html(
    old_email: str, new_email: str, user_name: str | None = None
) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"

    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("We received a request to change the email address on your Mizan account.", margin="0 0 6px")}
            {_p(f"Current email: <strong>{old_email}</strong>", margin="0 0 4px")}
            {_p(f"New email: <strong>{new_email}</strong>", margin="0 0 28px")}
            {_p("If you made this request, please check your new inbox for a verification code. If you did not make this request, please secure your account immediately and contact support.", margin="0 0 6px")}
        </td>
    </tr>
</table>"""

    post = f"""{body}
{safety_notice()}"""

    title = "Email change requested for Mizan"

    return _wraps(title, post, "")


def _legacy_email_change_confirmed_html(
    new_email: str, user_name: str | None = None
) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"

    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("Your Mizan account email has been successfully updated.", margin="0 0 6px")}
            {_p(f"Your new email is: <strong>{new_email}</strong>", margin="0 0 28px")}
            {_p("If you did not make this change, please contact support immediately.", margin="0 0 6px")}
        </td>
    </tr>
</table>"""

    post = f"""{body}
{safety_notice()}"""

    title = "Mizan email updated"

    return _wraps(title, post, "")


# ─────────────────────────────────────────────────────────────
# PASSWORD RESET EMAIL
# ─────────────────────────────────────────────────────────────


def _legacy_password_reset_email_html(token: str) -> str:
    link = f"{settings.APP_URL}/reset-password?token={token}"

    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p("Assalamu alaikum,", margin="0 0 8px")}
            {_p("We got a request to reset your Mizan password.", margin="0 0 6px")}
            {_p("No worries, it happens. Choose a new one below:", margin="0 0 28px")}
        </td>
    </tr>
</table>"""

    cta = cta_button(link, "Reset password")

    below_cta = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            {_p("Or paste this link into your browser:", size=13, color=BRAND_SUBTLE, margin="28px 0 12px")}
            <p style="
                font-family: {FONT_BODY};
                font-size: 12px;
                color: {BRAND_ACCENT};
                word-break: break-all;
                margin: 0;
                background-color: {BRAND_CODE_BG};
                padding: 12px 16px;
                border-radius: 10px;
                border: 1px solid {BRAND_CODE_BORDER};
                text-align: center;
            ">{link}</p>
            {_p("Didn't request this? Your password is still safe. Just ignore this email.", size=13, color=BRAND_SUBTLE, margin="18px 0 0")}
        </td>
    </tr>
</table>"""

    post = f"""{below_cta}
{safety_notice()}
{expiry_notice("This link expires in <strong>1 hour</strong> for your security.")}"""

    title = "Reset your Mizan password"

    return _wraps(
        title, body + cta + post, "This link expires in 1 hour for your security."
    )


# Clean, current templates. These definitions intentionally sit at the end of
# the module so they replace the older copy above without rewriting legacy
# mojibake in place.


def _code_block(value: str, label: str = "Your code") -> str:
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            {_p(label, size=13, color=BRAND_SUBTLE, margin="28px 0 14px")}
            <p style="
                font-family: {FONT_BODY};
                font-size: 32px;
                font-weight: 700;
                letter-spacing: 10px;
                color: {BRAND_ACCENT};
                word-break: break-all;
                margin: 0;
                background-color: {BRAND_CODE_BG};
                padding: 16px 20px;
                border-radius: 12px;
                border: 1px solid {BRAND_CODE_BORDER};
                text-align: center;
            ">{value}</p>
        </td>
    </tr>
</table>"""


def verification_email_html(token: str, user_name: str | None = None) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"
    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("We are really glad you are here.", margin="0 0 6px")}
            {_p("Mizan is a quiet space for small acts, reflection, and steady spiritual growth. Use the code below so we know this account belongs to you.", margin="0 0 28px")}
        </td>
    </tr>
</table>"""
    post = f"""{_code_block(token, "Your verification code")}
{_p("If this was not you, you can ignore this email. Nothing will change.", size=13, color=BRAND_SUBTLE, margin="18px 48px 0")}
{safety_notice()}
{expiry_notice("This code expires in <strong>24 hours</strong> for your security.")}"""
    return _wraps(
        "Welcome to Mizan, verify your email",
        body + post,
        "This code expires in 24 hours for your security.",
    )


def email_change_request_html(
    token: str, user_name: str | None = None, new_email: str = ""
) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"
    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("We received your request to change the email address on your Mizan account.", margin="0 0 6px")}
            {_p(f"New email: <strong>{new_email}</strong>", margin="0 0 6px")}
            {_p("Enter this code in Mizan to finish the change.", margin="0 0 28px")}
        </td>
    </tr>
</table>"""
    post = f"""{_code_block(token, "Your verification code")}
{_p("If this was not you, ignore this email and keep using your current address.", size=13, color=BRAND_SUBTLE, margin="18px 48px 0")}
{safety_notice()}
{expiry_notice("This code expires in <strong>24 hours</strong> for your security.")}"""
    return _wraps(
        "Verify your new Mizan email",
        body + post,
        "This code expires in 24 hours for your security.",
    )


def email_change_notification_html(
    old_email: str, new_email: str, user_name: str | None = None
) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"
    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("We received a request to change the email address on your Mizan account.", margin="0 0 6px")}
            {_p(f"Current email: <strong>{old_email}</strong>", margin="0 0 4px")}
            {_p(f"New email: <strong>{new_email}</strong>", margin="0 0 24px")}
            {_p("If you made this request, check your new inbox for the verification code. If you did not make this request, please change your password and contact support.", margin="0 0 6px")}
        </td>
    </tr>
</table>"""
    return _wraps("Email change requested for Mizan", body + safety_notice(), "")


def email_change_confirmed_html(new_email: str, user_name: str | None = None) -> str:
    first_name = user_name.split(" ")[0] if user_name else "friend"
    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p(f'Assalamu alaikum <strong style="color: {BRAND_INK};">{first_name}</strong>,', margin="0 0 8px")}
            {_p("Your Mizan account email has been updated.", margin="0 0 6px")}
            {_p(f"Your new email is: <strong>{new_email}</strong>", margin="0 0 24px")}
            {_p("If you did not make this change, please contact support right away.", margin="0 0 6px")}
        </td>
    </tr>
</table>"""
    return _wraps("Mizan email updated", body + safety_notice(), "")


def password_reset_email_html(token: str) -> str:
    link = f"{settings.APP_URL}/reset-password?token={token}"
    body = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding: 0 48px;">
            {_p("Assalamu alaikum,", margin="0 0 8px")}
            {_p("We received a request to reset your Mizan password.", margin="0 0 6px")}
            {_p("If that was you, choose a new password below. We will keep the link short-lived for your safety.", margin="0 0 28px")}
        </td>
    </tr>
</table>"""
    link_block = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 0 48px;">
            {_p("Or paste this link into your browser:", size=13, color=BRAND_SUBTLE, margin="28px 0 12px")}
            <p style="
                font-family: {FONT_BODY};
                font-size: 12px;
                color: {BRAND_ACCENT};
                word-break: break-all;
                margin: 0;
                background-color: {BRAND_CODE_BG};
                padding: 12px 16px;
                border-radius: 10px;
                border: 1px solid {BRAND_CODE_BORDER};
                text-align: center;
            ">{link}</p>
            {_p("If this was not you, ignore this email. Your current password will keep working.", size=13, color=BRAND_SUBTLE, margin="18px 0 0")}
        </td>
    </tr>
</table>"""
    post = f"""{link_block}
{safety_notice()}
{expiry_notice("This link expires in <strong>1 hour</strong> for your security.")}"""
    return _wraps(
        "Reset your Mizan password",
        body + cta_button(link, "Reset password") + post,
        "This link expires in 1 hour for your security.",
    )
