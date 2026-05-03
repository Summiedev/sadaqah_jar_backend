#!/usr/bin/env python
"""
Seed script for Sadaqah Jar database.
Populates the database with test users, acts, jars, logs, and family structures.

Usage:
    python -m app.seed.seed          # Run with default fixtures
    python -m app.seed.seed --clean  # Clean and reseed
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.badge import Badge
from app.models.charity import Charity
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog
from app.models.family_jar_member import FamilyJarMember
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User
from app.models.user_badge import UserBadge
from app.models.user_streak import UserStreak
from app.utils.invite import generate_invite_code


class DatabaseSeeder:
    """Manages database seeding with transaction rollback."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def clear_all(self):
        """Clear all tables in dependency order."""
        tables = [
            UserBadge, Badge, FamilyJarLog, FamilyJarMember, FamilyJar,
            SadaqahLog, Jar, UserStreak, SadaqahAct, User, Charity
        ]
        for table in tables:
            self.db.query(table).delete()
        self.db.commit()
        print("✓ Database cleared")
    
    def seed_users(self, count: int = 10) -> list[User]:
        """Create test users with diverse email/username patterns."""
        users = []
        created_count = 0
        
        # Create sample users with realistic names
        names = [
            ("fatima", "fatima@test.com"),
            ("ali", "ali@test.com"),
            ("aisha", "aisha@test.com"),
            ("omar", "omar@test.com"),
            ("zahra", "zahra@test.com"),
            ("hassan", "hassan@test.com"),
            ("leila", "leila@test.com"),
            ("karim", "karim@test.com"),
            ("amira", "amira@test.com"),
            ("yusuf", "yusuf@test.com"),
        ]
        
        for i in range(count):
            username, email = names[i] if i < len(names) else (f"user{i}", f"user{i}@test.com")

            user = self.db.query(User).filter(User.email == email).first()
            if user:
                user.username = username
                user.hashed_password = hash_password("password123")
                user.friday_reminder = True
                user.is_active = True
                user.evidence_mode = True
            else:
                user = User(
                    email=email,
                    username=username,
                    hashed_password=hash_password("password123"),  # plaintext: password123
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90))
                )
                self.db.add(user)
                created_count += 1

            users.append(user)
        
        self.db.commit()
        print(f"✓ Created {created_count} users")
        return users
    
    def seed_sadaqah_acts(self) -> list[SadaqahAct]:
        """Create diverse sadaqah acts with multipliers."""
        acts_data = [
            # Dhikr acts
            ("Say SubhanAllah 100 times", "dhikr", 1, 1.5),
            ("Say Alhamdulillah 100 times", "dhikr", 1, 1.5),
            ("Say La illaha illallah 100 times", "dhikr", 1, 1.5),
            ("Make dua for parents", "dhikr", 2, 2.0),
            ("Read Quran for 10 minutes", "dhikr", 2, 2.5),
            ("Learn a new Surah", "dhikr", 3, 3.0),
            
            # Donation acts
            ("Give Sadaqah to someone in need", "donation", 2, 2.5),
            ("Feed a poor person", "donation", 2, 2.0),
            ("Donate to charity online", "donation", 3, 2.5),
            ("Sponsor a child's education", "donation", 3, 3.0),
            
            # Community acts
            ("Smile at someone with intention", "community", 1, 1.0),
            ("Help a neighbour", "community", 2, 2.0),
            ("Remove harm from the road", "community", 2, 1.5),
            ("Visit a sick person", "community", 2, 2.0),
            ("Support someone emotionally", "community", 2, 2.0),
            
            # General acts
            ("Pray two rakah Nafil", "general", 2, 2.0),
            ("Attend Jumu'ah prayer", "general", 2, 3.0),
            ("Teach someone about Islam", "general", 3, 2.5),
            ("Daily affirmation (Intention-driven)", "general", 1, 1.0),
        ]
        
        acts = []
        for title, category, difficulty, ramadan_mult in acts_data:
            act = SadaqahAct(
                title=title,
                description=title,
                category=category,
                difficulty=difficulty,
                ramadan_multiplier=ramadan_mult,
                reward_weight=random.randint(1, 3),
                verified=True,
                is_ramadan_only=random.choice([False, False, False, True])  # 75% not ramadan-only
            )
            self.db.add(act)
            acts.append(act)
        
        self.db.commit()
        print(f"✓ Created {len(acts)} sadaqah acts")
        return acts
    
    def seed_charities(self) -> list[Charity]:
        """Create registered charities for users to donate to."""
        charities_data = [
            ("Islamic Relief", "Providing humanitarian aid globally", "https://www.islamic-relief.org", "humanitarian", True),
            ("IRUSA", "Supporting Muslim communities in USA", "https://irusa.org", "community", True),
            ("Muslim Hands", "Emergency relief and development", "https://muslimhands.org.uk", "humanitarian", True),
            ("Zakat Foundation", "Zakat distribution and social services", "https://www.zakat.org", "zakat", True),
            ("Human Appeal", "Humanitarian and development work", "https://humanappeal.org.uk", "humanitarian", False),
            ("Islamic Development Bank", "Supporting Islamic projects", "https://www.isdb.org", "development", False),
        ]
        
        charities = []
        for name, description, website_url, category, featured in charities_data:
            charity = Charity(
                name=name,
                description=description,
                website_url=website_url,
                category=category,
                is_verified=True,
                is_active=True,
                is_featured=featured,
            )
            self.db.add(charity)
            charities.append(charity)
        
        self.db.commit()
        print(f"✓ Created {len(charities)} charities")
        return charities
    
    def seed_jars(self, users: list[User]) -> list[Jar]:
        """Create personal jars for each user with varied progress."""
        jars = []
        
        for user in users:
            jar = Jar(
                user_id=user.id,
                capacity=33,
                current_stars=random.randint(0, 33),
                completed_at=None if random.random() > 0.3 else datetime.utcnow() - timedelta(days=random.randint(1, 60))
            )
            self.db.add(jar)
            jars.append(jar)
        
        self.db.commit()
        print(f"✓ Created {len(jars)} personal jars")
        return jars
    
    def seed_streaks(self, users: list[User]):
        """Create user streaks to simulate habit patterns."""
        for user in users:
            streak = UserStreak(
                user_id=user.id,
                current_streak=random.randint(0, 30),
                longest_streak=random.randint(5, 60),
                last_completed_date=date.today() - timedelta(days=random.randint(0, 5))
            )
            self.db.add(streak)
        
        self.db.commit()
        print(f"✓ Created {len(users)} user streaks")
    
    def seed_sadaqah_logs(self, users: list[User], acts: list[SadaqahAct], days_back: int = 60):
        """Create activity logs simulating 60 days of contributions."""
        log_count = 0
        used_logs = set()
        
        for user in users:
            # Each user does 10-40 logged acts
            for _ in range(random.randint(10, 40)):
                act = random.choice(acts)
                log_date = date.today() - timedelta(days=random.randint(0, days_back))
                
                # Prevent duplicates (same user, act, date)
                key = (user.id, act.id, log_date)
                if key in used_logs:
                    continue
                used_logs.add(key)
                
                # Calculate multipliers
                multiplier = act.reward_weight or 1.0
                is_friday = log_date.weekday() == 4
                is_ramadan_day = date(2026, 2, 17) <= log_date <= date(2026, 3, 18)
                
                if is_friday:
                    multiplier *= 2
                if is_ramadan_day:
                    multiplier *= act.ramadan_multiplier
                
                log = SadaqahLog(
                    user_id=user.id,
                    act_id=act.id,
                    date=log_date,
                    stars_earned=int(multiplier),
                    friday_boost=is_friday,
                    ramadan_bonus=is_ramadan_day,
                    created_at=datetime.combine(log_date, datetime.min.time())
                )
                self.db.add(log)
                log_count += 1
        
        self.db.commit()
        print(f"✓ Created {log_count} sadaqah logs")
    
    def seed_family_jars(self, users: list[User]) -> list[FamilyJar]:
        """Create family jars with members and contributions."""
        family_jars = []
        
        # Create 3 family jars with different group sizes
        group_configs = [
            ("The Righteous Givers", 5),
            ("Community Builders", 4),
            ("Ramadan Warriors", 3),
        ]
        
        for jar_name, group_size in group_configs:
            creator = random.choice(users)
            
            family_jar = FamilyJar(
                name=jar_name,
                capacity=100,
                current_stars=random.randint(20, 100),
                created_by=creator.id,
                invite_code=generate_invite_code(),
                is_active=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(7, 30))
            )
            self.db.add(family_jar)
            self.db.flush()  # Get the ID before creating members
            family_jars.append(family_jar)
        
        self.db.commit()
        
        # Add members to family jars
        for family_jar in family_jars:
            creator = self.db.query(User).filter(User.id == family_jar.created_by).first()
            
            # Add creator as member
            owner_member = FamilyJarMember(
                family_jar_id=family_jar.id,
                user_id=creator.id,
                role="creator",
                joined_at=family_jar.created_at
            )
            self.db.add(owner_member)
            
            # Add random members
            members_to_add = random.sample(
                [u for u in users if u.id != creator.id],
                min(random.randint(2, 4), len(users) - 1)
            )
            for member_user in members_to_add:
                member = FamilyJarMember(
                    family_jar_id=family_jar.id,
                    user_id=member_user.id,
                    role="member",
                    joined_at=family_jar.created_at + timedelta(days=random.randint(1, 10))
                )
                self.db.add(member)
        
        self.db.commit()
        print(f"✓ Created {len(family_jars)} family jars with members")
        return family_jars
    
    def seed_family_logs(self, family_jars: list[FamilyJar], acts: list[SadaqahAct], days_back: int = 30):
        """Create family jar contribution logs."""
        log_count = 0
        
        for family_jar in family_jars:
            # Get all members of this jar
            members = self.db.query(FamilyJarMember).filter(
                FamilyJarMember.family_jar_id == family_jar.id
            ).all()
            
            # Each jar gets 15-30 contributions
            for _ in range(random.randint(15, 30)):
                member = random.choice(members)
                act = random.choice(acts)
                log_date = date.today() - timedelta(days=random.randint(0, days_back))
                
                multiplier = act.reward_weight or 1.0
                is_friday = log_date.weekday() == 4
                
                if is_friday:
                    multiplier *= 2
                
                log = FamilyJarLog(
                    family_jar_id=family_jar.id,
                    user_id=member.user_id,
                    act_id=act.id,
                    date=log_date,
                    stars_added=int(multiplier * random.uniform(0.8, 1.2)),
                    created_at=datetime.combine(log_date, datetime.min.time())
                )
                self.db.add(log)
                log_count += 1
        
        self.db.commit()
        print(f"✓ Created {log_count} family jar logs")
    
    def seed_badges(self, users: list[User]):
        """Award badges to users based on activity levels."""
        badge_configs = [
            ("Generous Soul", "Gave Sadaqah consistently"),
            ("Streak Keeper", "Maintained a 7-day streak"),
            ("Community Champion", "Made 50+ contributions"),
            ("Friday Warrior", "Gave every Friday for a month"),
            ("Global Top 10", "Ranked in top 10 globally"),
        ]
        
        # Create badges
        badges = []
        for badge_name, description in badge_configs:
            badge = Badge(name=badge_name, description=description)
            self.db.add(badge)
            badges.append(badge)
        
        self.db.commit()
        
        # Award random badges to random users
        for user in users:
            selected_badges = random.sample(badges, k=random.randint(0, len(badges)))
            for badge in selected_badges:
                user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                self.db.add(user_badge)
        
        self.db.commit()
        print(f"✓ Created {len(badges)} badges and assigned to users")
    
    def run(self, clean: bool = False):
        """Execute the full seeding process."""
        try:
            if clean:
                self.clear_all()
            
            print("\n🌱 Starting database seeding...\n")
            
            users = self.seed_users(count=10)
            acts = self.seed_sadaqah_acts()
            charities = self.seed_charities()
            jars = self.seed_jars(users)
            self.seed_streaks(users)
            self.seed_sadaqah_logs(users, acts, days_back=60)
            family_jars = self.seed_family_jars(users)
            self.seed_family_logs(family_jars, acts, days_back=30)
            self.seed_badges(users)
            
            print("\n✅ Database seeding completed successfully!\n")
            print("📊 Summary:")
            print(f"   • {len(users)} users (all with password: password123)")
            print(f"   • {len(acts)} sadaqah acts")
            print(f"   • {len(charities)} registered charities")
            print(f"   • {len(jars)} personal jars")
            print(f"   • {len(family_jars)} family jars")
            print()
            
        except Exception as e:
            print(f"\n❌ Seeding failed: {str(e)}")
            self.db.rollback()
            sys.exit(1)
        finally:
            self.db.close()


def main():
    """CLI entry point for the seeder."""
    parser = argparse.ArgumentParser(description="Seed the Sadaqah Jar database")
    parser.add_argument("--clean", action="store_true", help="Clear and reseed the database")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    seeder = DatabaseSeeder(db)
    seeder.run(clean=args.clean)


if __name__ == "__main__":
    main()
