"""
Test script for ApplicationUser functionality
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from model.application_user import ApplicationUser, ApplicationUserCreate, Base
from service.application_user_service import ApplicationUserService

# Test database URL
DATABASE_URL = "sqlite+aiosqlite:///./test_application_users.db"

async def test_application_users():
    """Test ApplicationUser functionality"""
    
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        print("Testing ApplicationUser functionality...")
        
        # Test 1: Create user with auto-generated password
        print("\n1. Creating user with auto-generated password...")
        user_data = ApplicationUserCreate(
            name="Test Admin",
            email="test.admin@example.com",
            is_active=True
        )
        
        try:
            new_user = await ApplicationUserService.create_user(db, user_data, send_email=False)
            await db.commit()
            print(f"✓ User created with ID: {new_user.id}")
            print(f"✓ Generated password: {new_user.generated_password}")
            
            # Test 2: Authentication
            print("\n2. Testing authentication...")
            auth_user = await ApplicationUserService.authenticate_user(
                db, user_data.email, new_user.generated_password
            )
            if auth_user:
                print("✓ Authentication successful")
            else:
                print("✗ Authentication failed")
            
            # Test 3: Get user by email
            print("\n3. Testing get user by email...")
            retrieved_user = await ApplicationUserService.get_user_by_email(db, user_data.email)
            if retrieved_user:
                print(f"✓ User retrieved: {retrieved_user.name}")
            else:
                print("✗ User not found")
            
            # Test 4: Reset password
            print("\n4. Testing password reset...")
            reset_result = await ApplicationUserService.reset_password(
                db, new_user.id, send_email=False
            )
            await db.commit()
            if reset_result:
                print(f"✓ Password reset successful: {reset_result.generated_password}")
                
                # Test authentication with new password
                auth_new_pass = await ApplicationUserService.authenticate_user(
                    db, user_data.email, reset_result.generated_password
                )
                if auth_new_pass:
                    print("✓ Authentication with new password successful")
                else:
                    print("✗ Authentication with new password failed")
            else:
                print("✗ Password reset failed")
            
            # Test 5: Update user
            print("\n5. Testing user update...")
            from model.application_user import ApplicationUserUpdate
            update_data = ApplicationUserUpdate(
                name="Updated Test Admin",
                email="updated.admin@example.com"
            )
            updated_user = await ApplicationUserService.update_user(db, new_user.id, update_data)
            await db.commit()
            if updated_user:
                print(f"✓ User updated: {updated_user.name}, {updated_user.email}")
            else:
                print("✗ User update failed")
            
            # Test 6: Toggle status
            print("\n6. Testing status toggle...")
            toggled_user = await ApplicationUserService.toggle_user_status(db, new_user.id)
            await db.commit()
            if toggled_user:
                print(f"✓ Status toggled: {toggled_user.is_active}")
            else:
                print("✗ Status toggle failed")
            
            # Test 7: Delete user
            print("\n7. Testing user deletion...")
            delete_result = await ApplicationUserService.delete_user(db, new_user.id)
            await db.commit()
            if delete_result:
                print("✓ User deleted successfully")
            else:
                print("✗ User deletion failed")
                
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            await db.rollback()
    
    # Close engine
    await engine.dispose()
    print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_application_users())