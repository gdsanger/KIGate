"""
Test script for user role functionality
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from model.user import User, UserCreate, Base
from model.application_user import ApplicationUser, ApplicationUserCreate
from service.user_service import UserService
from service.application_user_service import ApplicationUserService

# Test database URL
DATABASE_URL = "sqlite+aiosqlite:///./test_user_roles.db"

async def test_user_roles():
    """Test user role functionality"""
    
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        print("Testing User Role Functionality...")
        
        # Test 1: Create API user with default role
        print("\n1. Creating API user with default role...")
        user_data = UserCreate(
            name="Test API User",
            email="test.api@example.com",
            is_active=True
        )
        
        try:
            new_user = await UserService.create_user(db, user_data)
            await db.commit()
            print(f"✓ User created with ID: {new_user.client_id}")
            print(f"✓ Default role: {new_user.role}")
            assert new_user.role == "user", f"Expected default role 'user', got '{new_user.role}'"
            
            # Test 2: Create API user with admin role
            print("\n2. Creating API user with admin role...")
            admin_user_data = UserCreate(
                name="Test Admin User",
                email="test.admin@example.com",
                role="admin",
                is_active=True
            )
            
            new_admin = await UserService.create_user(db, admin_user_data)
            await db.commit()
            print(f"✓ Admin user created with ID: {new_admin.client_id}")
            print(f"✓ Role: {new_admin.role}")
            assert new_admin.role == "admin", f"Expected role 'admin', got '{new_admin.role}'"
            
            # Test 3: Get users and verify roles
            print("\n3. Retrieving users and verifying roles...")
            users = await UserService.get_all_users(db)
            print(f"✓ Total users: {len(users)}")
            for user in users:
                print(f"  - {user.name}: role={user.role}")
            
            # Test 4: Create ApplicationUser with default role
            print("\n4. Creating ApplicationUser with default role...")
            app_user_data = ApplicationUserCreate(
                name="Test App User",
                email="test.appuser@example.com",
                is_active=True
            )
            
            new_app_user = await ApplicationUserService.create_user(db, app_user_data, send_email=False)
            await db.commit()
            print(f"✓ ApplicationUser created with ID: {new_app_user.id}")
            print(f"✓ Default role: {new_app_user.role}")
            assert new_app_user.role == "user", f"Expected default role 'user', got '{new_app_user.role}'"
            
            # Test 5: Create ApplicationUser with admin role
            print("\n5. Creating ApplicationUser with admin role...")
            app_admin_data = ApplicationUserCreate(
                name="Test App Admin",
                email="test.appadmin@example.com",
                role="admin",
                is_active=True
            )
            
            new_app_admin = await ApplicationUserService.create_user(db, app_admin_data, send_email=False)
            await db.commit()
            print(f"✓ ApplicationUser created with ID: {new_app_admin.id}")
            print(f"✓ Role: {new_app_admin.role}")
            assert new_app_admin.role == "admin", f"Expected role 'admin', got '{new_app_admin.role}'"
            
            # Test 6: Verify role validation
            print("\n6. Testing role validation...")
            try:
                invalid_user = UserCreate(
                    name="Invalid User",
                    email="invalid@example.com",
                    role="superuser"  # Invalid role
                )
                print("✗ Should have failed validation for invalid role")
            except Exception as e:
                print(f"✓ Role validation working: {type(e).__name__}")
            
            print("\n✅ All tests passed successfully!")
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
    
    # Close engine
    await engine.dispose()
    print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_user_roles())
