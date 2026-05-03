import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog
from app.models.jar import Jar
from app.models.family_jar import FamilyJar
from app.models.family_jar_member import FamilyJarMember
from app.models.family_jar_log import FamilyJarLog
from app.models.charity import Charity
from app.models.badge import Badge
from app.models.user_badge import UserBadge


db: Session = SessionLocal()


# -------------------------
# USERS
# -------------------------

users = []

for i in range(10):

    user = User(
        email=f"user{i}@test.com",
        username=f"user{i}",
        hashed_password="testpassword",
        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
    )

    db.add(user)
    users.append(user)

db.commit()

print("Users created")


# -------------------------
# SADAQAH ACTS
# -------------------------

acts_data = [
    ("Say SubhanAllah 100 times", "dhikr"),
    ("Give charity to someone", "donation"),
    ("Smile at someone", "community"),
    ("Help a neighbour", "community"),
    ("Pray two rakah", "general"),
    ("Make dua for parents", "dhikr"),
    ("Feed a poor person", "donation"),
    ("Read Quran for 10 minutes", "general"),
    ("Remove harm from road", "community"),
    ("Visit a sick person", "community"),
]

acts = []

for title, category in acts_data:

    act = SadaqahAct(
        title=title,
        description=title,
        category=category,
        difficulty=random.randint(1, 3),
        ramadan_multiplier=random.randint(1, 3),
        verified=True
    )

    db.add(act)
    acts.append(act)

db.commit()

print("Acts created")


# -------------------------
# JARS
# -------------------------

jars = []

for user in users:

    jar = Jar(
        user_id=user.id,
        capacity=33,
        current_stars=random.randint(0, 20)
    )

    db.add(jar)
    jars.append(jar)

db.commit()

print("Jars created")


# ----------------------------------
# SADAQAH LOGS (simulate 30 days)
# ----------------------------------

used_logs = set()

for user in users:

    for _ in range(random.randint(10, 40)):

        act = random.choice(acts)
        log_date = datetime.utcnow().date() - timedelta(days=random.randint(0, 30))

        key = (user.id, act.id, log_date)

        if key in used_logs:
            continue

        used_logs.add(key)

        log = SadaqahLog(
            user_id=user.id,
            act_id=act.id,
            date=log_date,
            stars_earned=random.randint(1, 3),
            friday_boost=random.choice([True, False]),
            ramadan_bonus=random.choice([True, False])
        )

        db.add(log)

print("Logs created")


# -------------------------
# FAMILY JARS
# -------------------------

# -------------------------
# FAMILY JAR
# -------------------------

family_jar = FamilyJar(
    name="Test Family Jar",
    invite_code="TEST123",
    capacity=100,
    current_stars=0,
    created_by=user.id
    
)

db.add(family_jar)
db.commit()
db.refresh(family_jar)

print("Family jar created")


# -------------------------
# FAMILY MEMBERS
# -------------------------

owner_member = FamilyJarMember(
    family_jar_id=family_jar.id,
    user_id=users[0].id
)

db.add(owner_member)

for user in users[1:5]:

    member = FamilyJarMember(
        family_jar_id=family_jar.id,
        user_id=user.id
    )

    db.add(member)

db.commit()

print("Family members created")
# -------------------------
# FAMILY LOGS
# -------------------------

for _ in range(30):

    member = random.choice(users[:5])
    act = random.choice(acts)

    log = FamilyJarLog(
        family_jar_id=family_jar.id,
        user_id=member.id,
        act_id=act.id,
        stars_added=random.randint(1, 3),
        date=datetime.utcnow().date()
    )

    db.add(log)

db.commit()

print("Family logs created")


# -------------------------
# CHARITIES
# -------------------------

charities = [

    ("Red Crescent", "https://redcrescent.org"),
    ("Islamic Relief", "https://islamic-relief.org"),
    ("Helping Hands", "https://helpinghands.org")

]

for name, url in charities:

    charity = Charity(
        name=name,
        website_url=url,
        description="Charity organization",
        category="humanitarian",
        is_verified=True,
        is_active=True
    )

    db.add(charity)

db.commit()

print("Charities created")


# -------------------------
# BADGES
# -------------------------

badge = Badge(
    name="First Good Deed",
    description="Completed your first sadaqah act",

)

db.add(badge)
db.commit()

print("Badges created")


# assign badge to random user

user_badge = UserBadge(
    user_id=users[0].id,
    badge_id=badge.id
)

db.add(user_badge)
db.commit()

print("User badges created")


print("SEED COMPLETE")