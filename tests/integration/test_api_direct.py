import requests

# Test login
login_response = requests.post(
    "http://localhost:8001/auth/login/",
    json={"email": "test@example.com", "password": "testpass123"}
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print("✅ Login successful")
    
    # Test conversations API
    conv_response = requests.get(
        "http://localhost:8001/api/v1/conversations/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"📊 Conversations API: {conv_response.status_code}")
    print(f"Response: {conv_response.text[:200]}...")
    
else:
    print(f"❌ Login failed: {login_response.status_code}")