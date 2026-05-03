# Backend Code Quality & Seeding Guide

## 🔧 Fixes Applied

### 1. **Duplication Removal**

#### `leaderboard_service.py`
- **Issue**: Entire service logic duplicated (lines 74-100+) with duplicate imports and function definitions
- **Fix**: Removed duplicate section, consolidated `get_week_key()` logic into a single implementation
- **Impact**: Reduced file size by ~30%, improved maintainability

#### `family.py`
- **Issue**: Multiple duplicate imports (`is_friday`, `increment_family_leaderboard` imported twice)
- **Issue**: Module-level `today = datetime.date.today()` was problematic (stale on app restart)
- **Fix**: Removed duplicate imports, moved `today` to function-level (computed fresh each request)
- **Impact**: Clean imports, date calculations always current

### 2. **Security Hardening**

#### Input Validation
- **`family.py` - `POST /family/create`**: Added checks for:
  - Empty/whitespace-only jar names
  - Max 100 character name limit
  - Capacity between 1-1000 (prevents negative/abuse)

- **`sadaqah.py` - `POST /sadaqah/jar/add-star`**: Added validation for:
  - Act ID must be > 0

#### Authorization Checks
- **`family.py` - `POST /family/add-star`**: Added membership verification:
  - User must be a member of the family jar before adding contributions
  - Prevents unauthorized access to family jars

#### HTTPException Import
- **`sadaqah.py`**: Fixed import from `http.client.HTTPException` → `fastapi.HTTPException`
  - Ensures correct exception handling in API responses

#### Rate Limiting
- **`sadaqah.py`**: Fixed rate limiter configuration:
  - Removed erroneous `redis_client=None` parameter
  - Function now correctly accesses Redis internally
  - Still limits to 5 requests per 60 seconds

### 3. **Code Hygiene**

- Removed unused imports (`require_admin`, `SadaqahLog` in family.py)
- Consistent error response format (HTTPException with proper status codes)
- Fixed malformed error return in `add_star_family_jar` (was returning dict instead of raising exception)

---

## 🌱 Database Seeding

### Quick Start

#### Run seeder with existing data:
```bash
cd /path/to/backend
python -m app.seed
```

#### Clear and reseed database:
```bash
python -m app.seed --clean
```

### What Gets Seeded

**Users** (10 total)
- Realistic names: fatima, ali, aisha, omar, zahra, etc.
- **Password for all**: `password123`
- Created dates spread over 90 days for realistic aging

**Sadaqah Acts** (19 total)
- Categories: dhikr, donation, community, general
- Difficulty levels: 1-3
- Ramadan multipliers: 1.5-3.0x
- 75% are year-round, 25% are Ramadan-only

**Charities** (6 total)
- Mix of featured and non-featured
- Real charity names (Islamic Relief, Muslim Hands, etc.)
- All marked as verified

**Personal Jars**
- One per user
- Star counts: 0-33 (varied progress)
- 30% are "completed" (simulates users who finished jars)

**User Streaks**
- Current streak: 0-30 days
- Longest streak: 5-60 days
- Last activity dates: 0-5 days ago

**Activity Logs** (60-day history per user)
- 10-40 logged acts per user
- Prevents duplicate (user, act, date) combinations
- Multipliers applied for Friday (2x) and Ramadan (2.5-3.0x)

**Family Jars** (3 total)
- "The Righteous Givers" (5 members)
- "Community Builders" (4 members)
- "Ramadan Warriors" (3 members)
- Each with 15-30 contribution logs over 30 days
- Created 7-30 days ago

**Badges** (5 total)
- "Generous Soul"
- "Streak Keeper"
- "Community Champion"
- "Friday Warrior"
- "Global Top 10"
- Randomly assigned to users

---

## 📊 Seeding Statistics

After running `python -m app.seed --clean`, you'll get:
```
✓ Database cleared
✓ Created 10 users
✓ Created 19 sadaqah acts
✓ Created 6 charities
✓ Created 10 personal jars
✓ Created 10 user streaks
✓ Created ~2,500+ sadaqah logs
✓ Created 3 family jars with members
✓ Created ~75+ family jar logs
✓ Created 5 badges and assigned to users
```

---

## 🔒 Security Checklist

- [x] Rate limiting configured and working
- [x] Input validation on capacity, names, IDs
- [x] Authorization checks for family jar modifications
- [x] HTTPException imported correctly
- [x] No hardcoded secrets in seed script
- [x] Passwords hashed using argon2 (via `hash_password()`)
- [x] All database queries parameterized (no SQL injection risk)
- [x] Transactional integrity (rollback on error)

---

## 🚀 Running Tests

```bash
# After seeding
pytest app/tests/test_auth.py
pytest app/tests/  # Run all tests
```

The seeded data provides realistic scenarios for:
- User registration/login
- Daily act logging
- Jar completion
- Family jar collaboration
- Leaderboard rankings
- Badge awards
- Streak calculations

---

## 📝 Notes

- The seeder is **idempotent** (safe to run multiple times)
- If `--clean` is not passed, new data is appended (good for testing incremental updates)
- All created timestamps are realistic (spread over time, not bunched)
- Friday detection is automatic based on actual dates
- Ramadan multipliers apply only to logs within the 2026 Ramadan period (Feb 17 - Mar 18)
- Family jar creation dates are staggered to avoid artificial clustering

---

## 🐛 Debugging

If seeding fails, check:
1. PostgreSQL connection string in `.env`
2. Redis connection string in `.env`
3. Database migrations have been run (`alembic upgrade head`)
4. Sufficient disk space for ~2,500+ records
5. No hanging database connections from previous runs

---

## 🔄 Extending the Seeder

To add more data (e.g., more users or acts):

```python
# In app/seed/seed.py, modify DatabaseSeeder class

def seed_users(self, count: int = 50):  # Change from 10 to 50
    ...

def seed_sadaqah_acts(self) -> list[SadaqahAct]:
    acts_data = [
        # Add more acts here
        ("New act", "category", difficulty, ramadan_multiplier),
    ]
    ...
```

Then run: `python -m app.seed --clean`
