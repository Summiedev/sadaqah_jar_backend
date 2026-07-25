from app.core.config import settings


# ─────────────────────────────────────────────────────────────
# BRAND COLOURS
# ─────────────────────────────────────────────────────────────

BRAND_BG = "#F5F0E8"  # warm cream paper
BRAND_CARD = "#FFFFFF"
BRAND_INK = "#1E1A17"  # warm near-black
BRAND_MUTED = "#6B5E52"
BRAND_SUBTLE = "#8A7B6E"
BRAND_LINE = "#E8DFD4"
BRAND_EMERALD = "#047857"  # rich emerald green for CTAs
BRAND_EMERALD_DARK = "#065F46"
BRAND_GOLD = "#B08D57"  # subtle gold accent for geometry
BRAND_GOLD_LIGHT = "#D4C4A8"


# ─────────────────────────────────────────────────────────────
# TYPOGRAPHY
# ─────────────────────────────────────────────────────────────

FONT_STACK = '"Georgia", "Times New Roman", serif'
FONT_BODY = '"Inter", "Helvetica Neue", Arial, sans-serif'


# ─────────────────────────────────────────────────────────────
# LAYOUT CONSTANTS
# ─────────────────────────────────────────────────────────────

CARD_MAX_WIDTH = "560px"
CARD_RADIUS = "16px"
BUTTON_RADIUS = "10px"
SECTION_GAP = "28px"


# ─────────────────────────────────────────────────────────────
# REUSABLE HTML FRAGMENTS
# ─────────────────────────────────────────────────────────────

def _doctype() -> str:
    return "<!DOCTYPE html>"


def _html_open() -> str:
    return (
        '<html lang="en" xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">'
    )


def _head(title: str) -> str:
    return f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{title}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style type="text/css">
        /* Reset */
        body, table, td, p, a, li, blockquote {{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; }}
        a {{ text-decoration: none; color: inherit; }}
        
        /* Mobile */
        @media screen and (max-width: 600px) {{
            .email-container {{
                width: 100% !important;
                max-width: 100% !important;
            }}
            .fluid {{
                width: 100% !important;
                max-width: 100% !important;
                height: auto !important;
            }}
            .stack-column {{
                display: block !important;
                width: 100% !important;
                max-width: 100% !important;
            }}
            .mobile-padding {{
                padding-left: 24px !important;
                padding-right: 24px !important;
            }}
            .mobile-font {{
                font-size: 14px !important;
            }}
            .hero-title {{
                font-size: 22px !important;
            }}
        }}
    </style>
</head>"""


def _body_open(body_style: str = "") -> str:
    background = f'background-color: {BRAND_BG};'
    return f'<body style="{background} {body_style} margin: 0; padding: 0; width: 100%; -webkit-font-smoothing: antialiased;">'


def _body_close() -> str:
    return "</body>"


def _html_close() -> str:
    return "</html>"


# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# HEADER / LOGO AREA
# ─────────────────────────────────────────────────────────────

_MIZAN_LOGO_DATA_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIj4KICA8cmVjdCB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgcng9IjEyMCIgZmlsbD0iIzExMGUwYyIvPgogIDxnIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2RmYmE2YiIgc3Ryb2tlLXdpZHRoPSIxOCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+CiAgICA8cGF0aCBkPSJNMjU2IDExOCBMMzY4IDI1NiBMMjU2IDM5NCBMMTQ0IDI1NiBaIi8+CiAgICA8cGF0aCBkPSJNMjU2IDE3NCBMMzIyIDI1NiBMMjU2IDMzOCBMMTkwIDI1NiBaIi8+CiAgPC9nPgogIDxjaXJjbGUgY3g9IjI1NiIgY3k9IjI1NiIgcj0iMjAiIGZpbGw9IiNkZmJhNmIiLz4KPC9zdmc+Cg=="


def header_section() -> str:
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {BRAND_CARD};">
    <tr>
        <td align="center" style="padding: 36px 30px 28px;">
            <img src="{_MIZAN_LOGO_DATA_URI}" alt="Mizan" width="64" height="64" style="display: block; margin: 0 auto 18px; border: 0;">
            <h1 style="
                font-family: {FONT_STACK};
                font-size: 26px;
                font-weight: 700;
                color: {BRAND_INK};
                margin: 0;
                letter-spacing: 1.5px;
            ">Mizan</h1>
            <p style="
                font-family: {FONT_BODY};
                font-size: 11px;
                font-weight: 500;
                color: {BRAND_GOLD};
                margin: 6px 0 0;
                letter-spacing: 2.5px;
                text-transform: uppercase;
            ">Sanctuary for the soul</p>
        </td>
    </tr>
</table>"""  # noqa: E501


# ─────────────────────────────────────────────────────────────
# CARD WRAPPER
# ─────────────────────────────────────────────────────────────

def card_open(padding_top: str = "40px", padding_bottom: str = "40px") -> str:
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {BRAND_BG};">
    <tr>
        <td align="center" style="padding: 0 20px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: {CARD_MAX_WIDTH}; background-color: {BRAND_CARD}; border-radius: {CARD_RADIUS}; overflow: hidden; box-shadow: 0 4px 24px rgba(30, 26, 23, 0.06);">
                <tr>
                    <td class="mobile-padding" style="padding: {padding_top} 48px {padding_bottom};">
"""


def card_close() -> str:
    return """                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>"""


# ─────────────────────────────────────────────────────────────
# BUTTONS
# ─────────────────────────────────────────────────────────────

def cta_button(url: str, text: str) -> str:
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin: 32px auto;">
    <tr>
        <td align="center" style="border-radius: {BUTTON_RADIUS}; background-color: {BRAND_EMERALD};">
            <a href="{url}" style="
                display: inline-block;
                padding: 16px 36px;
                font-family: {FONT_BODY};
                font-size: 15px;
                font-weight: 600;
                color: #FFFFFF;
                text-decoration: none;
                border-radius: {BUTTON_RADIUS};
                letter-spacing: 0.3px;
            ">{text}</a>
        </td>
    </tr>
</table>"""


# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

def footer_section() -> str:
    support_email = getattr(settings, "FROM_EMAIL", "hello@mizan.app") or "hello@mizan.app"
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {BRAND_CARD};">
    <tr>
        <td align="center" style="padding: 32px 30px 40px;">
            <!-- Geometric divider -->
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin: 0 auto 24px;">
                <tr>
                    <td align="center" style="font-size: 14px; color: {BRAND_GOLD}; letter-spacing: 3px; line-height: 1;">
                        &#x2756; &#x2756; &#x2756;
                    </td>
                </tr>
            </table>
            <p style="
                font-family: {FONT_BODY};
                font-size: 13px;
                color: {BRAND_SUBTLE};
                margin: 0 0 6px;
            ">Need help? <a href="mailto:{support_email}" style="color: {BRAND_EMERALD}; text-decoration: none; font-weight: 500;">{support_email}</a></p>
            <p style="
                font-family: {FONT_BODY};
                font-size: 11px;
                color: {BRAND_SUBTLE};
                margin: 0;
            ">&copy; 2026 Mizan. All rights reserved.</p>
        </td>
    </tr>
</table>"""


# ─────────────────────────────────────────────────────────────
# SAFETY NOTICE (for unintended requests)
# ─────────────────────────────────────────────────────────────

def safety_notice() -> str:
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #FDFBF7; border-left: 3px solid {BRAND_GOLD_LIGHT};">
    <tr>
        <td style="padding: 20px 24px;">
            <p style="
                font-family: {FONT_BODY};
                font-size: 13px;
                color: {BRAND_MUTED};
                margin: 0;
                line-height: 1.65;
            ">If you did not initiate this request, please disregard this email. Your account remains secure and no changes have been made.</p>
        </td>
    </tr>
</table>"""


# ─────────────────────────────────────────────────────────────
# EXPIRY NOTICE
# ─────────────────────────────────────────────────────────────

def expiry_notice(expiry_text: str) -> str:
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 24px 48px 0;">
            <p style="
                font-family: {FONT_BODY};
                font-size: 12px;
                color: {BRAND_SUBTLE};
                margin: 0;
            ">{expiry_text}</p>
        </td>
    </tr>
</table>"""
