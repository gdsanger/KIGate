"""
Test script for admin authentication functionality
"""
import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Opg#842+9914"

async def test_admin_authentication():
    """Test admin authentication functionality"""
    print("Testing admin authentication...")
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Access admin without credentials (should return 401)
        print("\n1. Testing access without credentials...")
        response = await client.get(f"{BASE_URL}/admin", follow_redirects=True)
        print(f"Status without auth: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Test 2: Access admin with wrong credentials (should return 401)
        print("2. Testing access with wrong credentials...")
        auth = ("admin", "wrongpassword")
        response = await client.get(f"{BASE_URL}/admin", auth=auth, follow_redirects=True)
        print(f"Status with wrong auth: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Test 3: Access admin with correct credentials (should return 200)
        print("3. Testing access with correct credentials...")
        auth = (ADMIN_USERNAME, ADMIN_PASSWORD)
        response = await client.get(f"{BASE_URL}/admin", auth=auth, follow_redirects=True)
        print(f"Status with correct auth: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Test 4: Access admin users page with correct credentials
        print("4. Testing admin users page access...")
        response = await client.get(f"{BASE_URL}/admin/users", auth=auth)
        print(f"Status for /admin/users: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Test 5: Access login page without credentials (should work)
        print("5. Testing login page access...")
        response = await client.get(f"{BASE_URL}/admin/login")
        print(f"Status for login page: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Test 6: Test other admin API endpoints
        print("6. Testing admin API endpoints protection...")
        endpoints = [
            "/admin/api/users/test-id",
        ]
        
        for endpoint in endpoints:
            # Without auth
            response = await client.get(f"{BASE_URL}{endpoint}")
            print(f"Status for {endpoint} without auth: {response.status_code}")
            assert response.status_code == 401, f"Expected 401 for {endpoint}, got {response.status_code}"
            
            # With auth (might return 404 for non-existent user, but should not be 401)
            response = await client.get(f"{BASE_URL}{endpoint}", auth=auth)
            print(f"Status for {endpoint} with auth: {response.status_code}")
            assert response.status_code != 401, f"Should not return 401 with auth for {endpoint}"
    
    print("\n✅ All admin authentication tests passed!")

async def main():
    """Run all tests"""
    try:
        await test_admin_authentication()
        print("\n🎉 All tests passed! Admin authentication is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())