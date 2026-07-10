from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Base.metadata is populated.
import app.models.adhkar  # noqa: F401
import app.models.badge  # noqa: F401
import app.models.charity  # noqa: F401
import app.models.device_token  # noqa: F401
import app.models.donation_intent  # noqa: F401
import app.models.email_verification_token  # noqa: F401
import app.models.evidence  # noqa: F401
import app.models.family_badge  # noqa: F401
import app.models.family_jar  # noqa: F401
import app.models.family_jar_log  # noqa: F401
import app.models.family_jar_member  # noqa: F401
import app.models.jar  # noqa: F401
import app.models.leaderboard_season  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.password_reset_token  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.sadaqah_act  # noqa: F401
import app.models.sadaqah_log  # noqa: F401
import app.models.user  # noqa: F401
import app.models.user_badge  # noqa: F401
import app.models.user_streak  # noqa: F401
