from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Base.metadata is populated.
import app.models.badge  # noqa: E402,F401
import app.models.charity  # noqa: E402,F401
import app.models.donation_intent  # noqa: E402,F401
import app.models.evidence  # noqa: E402,F401
import app.family.models  # noqa: E402,F401
import app.goals.models  # noqa: E402,F401
import app.journey.models  # noqa: E402,F401
import app.books.models  # noqa: E402,F401
import app.models.jar  # noqa: E402,F401
import app.models.leaderboard_season  # noqa: E402,F401
import app.notifications.models  # noqa: E402,F401
import app.models.sadaqah_act  # noqa: E402,F401
import app.models.sadaqah_log  # noqa: E402,F401
import app.models.user_badge  # noqa: E402,F401
import app.models.user_streak  # noqa: E402,F401
import app.users.models  # noqa: E402,F401
import app.sadaqah.models  # noqa: E402,F401
