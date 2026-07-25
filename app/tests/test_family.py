"""Tests for Family domain API.

Frontend source of truth — covers every endpoint the frontend app calls:
- POST /family/create
- POST /family/join
- GET  /family/
- GET  /family/{family_id}
- GET  /family/{family_id}/members
- DELETE /family/{family_id}/members/{member_id}
- POST /family/{family_id}/goals
- GET  /family/{family_id}/goals
- PATCH /family/{family_id}/goals/{goal_id}
- DELETE /family/{family_id}/goals/{goal_id}
- POST /family/{family_id}/goals/{goal_id}/archive
- POST /family/{family_id}/goals/{goal_id}/complete
- POST /family/{family_id}/prayers
- GET  /family/{family_id}/prayers
- POST /family/{family_id}/prayers/{prayer_id}/respond
- POST /family/{family_id}/reflections
- GET  /family/{family_id}/reflections
- DELETE /family/{family_id}/reflections/{reflection_id}
- POST /family/{family_id}/reflections/{reflection_id}/encourage
- GET  /family/{family_id}/settings
- PATCH /family/{family_id}/settings
- POST /family/{family_id}/archive
- DELETE /family/{family_id}
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user import User, Role
from app.family.models import (
    Family,
    FamilyMember,
    FamilyGoal,
    PrayerRequest,
    FamilyReflection,
    FamilySettings,
    ReflectionEncouragement,
    PrayerRequestResponse,
)

client = TestClient(app)

API = "/api/v1"


def _headers(user_id: int, role: str = "USER") -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user_id), 'role': role})}"}


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


def _create_user(db, username, email, role=Role.USER) -> User:
    u = User(username=username, email=email, hashed_password=hash_password("TestPass123"), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _create_family(db, owner_id, name="Test Family") -> Family:
    f = Family(name=name, cover_icon="🌿", invite_code="TEST-CODE", created_by=owner_id)
    db.add(f)
    db.commit()
    db.refresh(f)
    db.add(FamilyMember(family_id=f.id, user_id=owner_id, role_name="owner"))
    db.add(FamilySettings(family_id=f.id, notification_preferences={}, version=1))
    db.commit()
    db.refresh(f)
    return f


def _clean_family(db, family_id):
    db.query(ReflectionEncouragement).filter(ReflectionEncouragement.reflection_id.in_(
        db.query(FamilyReflection.id).filter(FamilyReflection.family_id == family_id)
    )).delete(synchronize_session=False)
    db.query(FamilyReflection).filter(FamilyReflection.family_id == family_id).delete(synchronize_session=False)
    db.query(PrayerRequestResponse).filter(PrayerRequestResponse.prayer_request_id.in_(
        db.query(PrayerRequest.id).filter(PrayerRequest.family_id == family_id)
    )).delete(synchronize_session=False)
    db.query(PrayerRequest).filter(PrayerRequest.family_id == family_id).delete(synchronize_session=False)
    db.query(FamilyGoal).filter(FamilyGoal.family_id == family_id).delete(synchronize_session=False)
    db.query(FamilyMember).filter(FamilyMember.family_id == family_id).delete(synchronize_session=False)
    db.query(FamilySettings).filter(FamilySettings.family_id == family_id).delete(synchronize_session=False)
    db.query(Family).filter(Family.id == family_id).delete(synchronize_session=False)
    db.commit()


# Family domain requires PostgreSQL (JSONB columns); skip on SQLite.
@pytest.fixture(autouse=True)
def _skip_on_sqlite():
    if engine.dialect.name == "sqlite":
        pytest.skip("Family domain requires PostgreSQL (JSONB columns)")


# ---------------------------------------------------------------------------
# Create / Join / List
# ---------------------------------------------------------------------------


def test_create_family(db):
    owner = _create_user(db, "fam_owner_create", "fam_owner_create@test.com")
    resp = client.post(f"{API}/family/create", params={"name": "My Family"}, headers=_headers(owner.id))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "My Family"
    assert "invite_code" in data
    _clean_family(db, data["id"])


def test_join_family(db):
    owner = _create_user(db, "join_owner_2", "join_owner_2@test.com")
    family = _create_family(db, owner.id, name="Joinable")
    member = _create_user(db, "join_member_2", "join_member_2@test.com")

    resp = client.post(f"{API}/family/join", params={"invite_code": family.invite_code}, headers=_headers(member.id))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == family.id
    _clean_family(db, family.id)


def test_list_families(db):
    owner = _create_user(db, "list_owner_2", "list_owner_2@test.com")
    family = _create_family(db, owner.id, name="Listed")

    resp = client.get(f"{API}/family/", headers=_headers(owner.id))
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()["data"]]
    assert "Listed" in names
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


def test_get_family_detail(db):
    owner = _create_user(db, "detail_owner_2", "detail_owner_2@test.com")
    family = _create_family(db, owner.id, name="Detail Fam")

    resp = client.get(f"{API}/family/{family.id}", headers=_headers(owner.id))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Detail Fam"
    assert len(data["members"]) >= 1
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


def test_remove_member(db):
    owner = _create_user(db, "rem_owner_2", "rem_owner_2@test.com")
    family = _create_family(db, owner.id, name="Remove Fam")
    member = _create_user(db, "rem_target_2", "rem_target_2@test.com")

    join_resp = client.post(f"{API}/family/join", params={"invite_code": family.invite_code}, headers=_headers(member.id))
    assert join_resp.status_code == 200

    members_resp = client.get(f"{API}/family/{family.id}/members", headers=_headers(owner.id))
    assert members_resp.status_code == 200
    target_member = next(m for m in members_resp.json()["data"] if m["user_id"] == member.id)

    del_resp = client.delete(
        f"{API}/family/{family.id}/members/{target_member['id']}",
        headers=_headers(owner.id),
    )
    assert del_resp.status_code == 200
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


def test_create_and_list_goals(db):
    owner = _create_user(db, "goal_owner_2", "goal_owner_2@test.com")
    family = _create_family(db, owner.id, name="Goal Fam")

    create = client.post(
        f"{API}/family/{family.id}/goals",
        json={"title": "Read Quran", "acts_target": 10},
        headers=_headers(owner.id),
    )
    assert create.status_code == 201
    goal_id = create.json()["data"]["id"]

    listed = client.get(f"{API}/family/{family.id}/goals", headers=_headers(owner.id))
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["title"] == "Read Quran"
    _clean_family(db, family.id)


def test_update_goal(db):
    owner = _create_user(db, "upd_goal_owner_2", "upd_goal_owner_2@test.com")
    family = _create_family(db, owner.id, name="Upd Goal Fam")
    goal = FamilyGoal(family_id=family.id, created_by=owner.id, title="Old", acts_target=5, acts_done=2)
    db.add(goal)
    db.commit()
    db.refresh(goal)

    resp = client.patch(
        f"{API}/family/{family.id}/goals/{goal.id}",
        json={"title": "New Title", "acts_done": 5},
        headers=_headers(owner.id),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "New Title"
    assert resp.json()["data"]["acts_done"] == 5
    _clean_family(db, family.id)


def test_delete_goal(db):
    owner = _create_user(db, "del_goal_owner_2", "del_goal_owner_2@test.com")
    family = _create_family(db, owner.id, name="Del Goal Fam")
    goal = FamilyGoal(family_id=family.id, created_by=owner.id, title="ToDelete", acts_target=1)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id

    resp = client.delete(f"{API}/family/{family.id}/goals/{goal_id}", headers=_headers(owner.id))
    assert resp.status_code == 200

    db.expire_all()
    gone = db.query(FamilyGoal).filter(FamilyGoal.id == goal_id).first()
    assert gone is None
    _clean_family(db, family.id)


def test_complete_goal(db):
    owner = _create_user(db, "comp_goal_owner_2", "comp_goal_owner_2@test.com")
    family = _create_family(db, owner.id, name="Complete Goal Fam")
    goal = FamilyGoal(family_id=family.id, created_by=owner.id, title="Complete Me", acts_target=1)
    db.add(goal)
    db.commit()
    db.refresh(goal)

    resp = client.post(f"{API}/family/{family.id}/goals/{goal.id}/complete", headers=_headers(owner.id))
    assert resp.status_code == 200
    assert resp.json()["data"]["completed_at"] is not None
    _clean_family(db, family.id)


def test_archive_goal(db):
    owner = _create_user(db, "arch_goal_owner_2", "arch_goal_owner_2@test.com")
    family = _create_family(db, owner.id, name="Archive Goal Fam")
    goal = FamilyGoal(family_id=family.id, created_by=owner.id, title="Archive Me", acts_target=1)
    db.add(goal)
    db.commit()
    db.refresh(goal)

    resp = client.post(f"{API}/family/{family.id}/goals/{goal.id}/archive", headers=_headers(owner.id))
    assert resp.status_code == 200

    db.expire_all()
    assert goal.is_archived is True
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Prayers
# ---------------------------------------------------------------------------


def test_create_and_list_prayers(db):
    owner = _create_user(db, "prayer_owner_2", "prayer_owner_2@test.com")
    family = _create_family(db, owner.id, name="Prayer Fam")

    create = client.post(
        f"{API}/family/{family.id}/prayers",
        json={"text": "Please pray for my exams", "is_private": False},
        headers=_headers(owner.id),
    )
    assert create.status_code == 201
    prayer_id = create.json()["data"]["id"]

    listed = client.get(f"{API}/family/{family.id}/prayers", headers=_headers(owner.id))
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["text"] == "Please pray for my exams"
    _clean_family(db, family.id)


def test_respond_to_prayer(db):
    owner = _create_user(db, "prayer_resp_owner_2", "prayer_resp_owner_2@test.com")
    family = _create_family(db, owner.id, name="PrayerResp Fam")
    member = _create_user(db, "prayer_resp_member_2", "prayer_resp_member_2@test.com")
    join_resp = client.post(f"{API}/family/join", params={"invite_code": family.invite_code}, headers=_headers(member.id))
    assert join_resp.status_code == 200

    prayer = PrayerRequest(family_id=family.id, author_id=owner.id, text="Heal my heart", is_private=False)
    db.add(prayer)
    db.commit()
    db.refresh(prayer)

    resp = client.post(
        f"{API}/family/{family.id}/prayers/{prayer.id}/respond",
        json={"response_type": "ameen"},
        headers=_headers(member.id),
    )
    assert resp.status_code == 200
    assert "response_counts" in resp.json()["data"]
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


def test_create_and_list_reflections(db):
    owner = _create_user(db, "refl_owner_2", "refl_owner_2@test.com")
    family = _create_family(db, owner.id, name="Reflection Fam")

    create = client.post(
        f"{API}/family/{family.id}/reflections",
        json={"text": "Alhamdulillah for today"},
        headers=_headers(owner.id),
    )
    assert create.status_code == 201
    refl_id = create.json()["data"]["id"]

    listed = client.get(f"{API}/family/{family.id}/reflections", headers=_headers(owner.id))
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["text"] == "Alhamdulillah for today"
    _clean_family(db, family.id)


def test_delete_reflection(db):
    owner = _create_user(db, "del_refl_owner_2", "del_refl_owner_2@test.com")
    family = _create_family(db, owner.id, name="Del Refl Fam")
    refl = FamilyReflection(family_id=family.id, author_id=owner.id, text="Temp reflection")
    db.add(refl)
    db.commit()
    db.refresh(refl)
    refl_id = refl.id

    resp = client.delete(f"{API}/family/{family.id}/reflections/{refl_id}", headers=_headers(owner.id))
    assert resp.status_code == 200

    db.expire_all()
    gone = db.query(FamilyReflection).filter(FamilyReflection.id == refl_id).first()
    assert gone is None
    _clean_family(db, family.id)


def test_encourage_reflection(db):
    owner = _create_user(db, "enc_refl_owner_2", "enc_refl_owner_2@test.com")
    family = _create_family(db, owner.id, name="Enc Refl Fam")
    member = _create_user(db, "enc_refl_member_2", "enc_refl_member_2@test.com")
    join_resp = client.post(f"{API}/family/join", params={"invite_code": family.invite_code}, headers=_headers(member.id))
    assert join_resp.status_code == 200

    refl = FamilyReflection(family_id=family.id, author_id=owner.id, text="Beautiful day")
    db.add(refl)
    db.commit()
    db.refresh(refl)

    resp = client.post(
        f"{API}/family/{family.id}/reflections/{refl.id}/encourage",
        json={"encouragement_type": "ameen"},
        headers=_headers(member.id),
    )
    assert resp.status_code == 200
    assert "encouragement_counts" in resp.json()["data"]
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_get_and_update_settings(db):
    owner = _create_user(db, "settings_owner_2", "settings_owner_2@test.com")
    family = _create_family(db, owner.id, name="Settings Fam")

    get_resp = client.get(f"{API}/family/{family.id}/settings", headers=_headers(owner.id))
    assert get_resp.status_code == 200
    assert "notification_preferences" in get_resp.json()["data"]

    patch_resp = client.patch(
        f"{API}/family/{family.id}/settings",
        json={"notification_preferences": {"prayer": True, "reflection": False}},
        headers=_headers(owner.id),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["notification_preferences"]["prayer"] is True
    _clean_family(db, family.id)


# ---------------------------------------------------------------------------
# Archive / Delete
# ---------------------------------------------------------------------------


def test_archive_family(db):
    owner = _create_user(db, "archive_owner_2", "archive_owner_2@test.com")
    family = _create_family(db, owner.id, name="Archive Fam")

    resp = client.post(f"{API}/family/{family.id}/archive", headers=_headers(owner.id))
    assert resp.status_code == 200
    assert "archived" in resp.json().get("message", "").lower()

    db.expire_all()
    family = db.query(Family).filter(Family.id == family.id).first()
    assert family.deleted_at is not None
    _clean_family(db, family.id)


def test_delete_family(db):
    owner = _create_user(db, "del_fam_owner_2", "del_fam_owner_2@test.com")
    family = _create_family(db, owner.id, name="Delete Fam")

    resp = client.delete(f"{API}/family/{family.id}", headers=_headers(owner.id))
    assert resp.status_code == 200

    db.expire_all()
    found = db.query(Family).filter(Family.id == family.id).first()
    assert found is None


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


def test_family_endpoints_require_auth(db):
    resp = client.get(f"{API}/family/")
    assert resp.status_code == 403

    resp = client.post(f"{API}/family/create", params={"name": "No Auth"})
    assert resp.status_code == 403
