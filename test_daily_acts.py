#!/usr/bin/env python
import requests

# Test login and daily acts endpoint
login_data = {"email": "fatima@test.com", "password": "password123"}
login_response = requests.post(
    "https://sadaqah-jar-backend.onrender.com/auth/login", json=login_data, timeout=30
)
print(f"Login Status: {login_response.status_code}")
login_json = login_response.json()

if login_response.status_code == 200 and "access_token" in login_json:
    token = login_json["access_token"]
    print("[OK] Got token")

    # Test daily acts endpoint
    headers = {"Authorization": f"Bearer {token}"}
    daily_response = requests.get(
        "https://sadaqah-jar-backend.onrender.com/sadaqah/daily",
        headers=headers,
        timeout=30,
    )
    print(f"Daily Acts Status: {daily_response.status_code}")
    daily_json = daily_response.json()

    if daily_response.status_code == 200:
        if isinstance(daily_json, list):
            print(f"[OK] Daily Acts Count: {len(daily_json)}")
            if len(daily_json) > 0:
                print(f"[OK] First act: {daily_json[0].get('title')}")
                print("[OK] Daily acts endpoint is working!")
        else:
            print(f"Response type: {type(daily_json)}")
    else:
        print(f"Error: {daily_json}")
else:
    print(f"Login failed: {login_json}")
