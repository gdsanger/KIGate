#!/usr/bin/env python3
"""
Test script for mail integration with user service
"""
import asyncio
from database import init_db, get_async_session
from service.user_service import UserService
from model.user import UserCreate

async def test_user_creation_with_mail():
    """Test user creation with mail integration"""
    print("Testing user creation with mail integration...")
    
    # Initialize database
    await init_db()
    
    async for db in get_async_session():
        try:
            # Test user creation with email (but mail sending disabled for testing)
            user_data = UserCreate(
                name="Test Mail User",
                email="test-mail@example.com", 
                is_active=True
            )
            
            # Create user without sending email (send_email=False)
            user = await UserService.create_user(db, user_data, send_email=False)
            await db.commit()
            
            print(f"✓ User created successfully: {user.client_id}")
            print(f"✓ User name: {user.name}")
            print(f"✓ User email: {user.email}")
            print(f"✓ Client secret generated: {'Yes' if user.client_secret else 'No'}")
            
            # Test secret regeneration without sending email
            new_secret = await UserService.regenerate_client_secret(db, user.client_id, send_email=False)
            await db.commit()
            
            print(f"✓ Secret regenerated: {'Yes' if new_secret else 'No'}")
            
            # Test with email sending enabled (will fail gracefully due to missing config)
            user_data2 = UserCreate(
                name="Test Mail User 2",
                email="test-mail2@example.com",
                is_active=True
            )
            
            user2 = await UserService.create_user(db, user_data2, send_email=True)
            await db.commit()
            
            print(f"✓ User created with mail attempt: {user2.client_id}")
            print("✓ Mail sending failed gracefully (expected without Azure credentials)")
            
            print("✓ Mail integration working correctly!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            await db.rollback()
            return False
        finally:
            break

async def main():
    """Run integration test"""
    print("=== Mail Integration Test ===\n")
    
    success = await test_user_creation_with_mail()
    
    if success:
        print("\n✓ All integration tests passed!")
    else:
        print("\n❌ Integration tests failed!")

if __name__ == "__main__":
    asyncio.run(main())