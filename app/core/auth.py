"""Compatibility imports for legacy modules.

Authentication dependencies are owned by ``app.users.dependencies``.  This
module remains until legacy product modules are migrated feature by feature.
"""

from app.users.dependencies import get_current_user, oauth2_scheme

__all__ = ["get_current_user", "oauth2_scheme"]
