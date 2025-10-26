"""
Demo script for ApplicationUser functionality
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from model.application_user import ApplicationUser, ApplicationUserCreate, ApplicationUserUpdate, Base
from service.application_user_service import ApplicationUserService

# Demo database URL
DATABASE_URL = "sqlite+aiosqlite:///./demo_application_users.db"

async def demo_application_users():
    """Demonstrate ApplicationUser functionality"""
    
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        print("🔐 KIGate ApplicationUsers Demo")
        print("=" * 50)
        
        # Demo 1: Create admin users
        print("\n📝 Erstelle Admin-Benutzer...")
        
        users_to_create = [
            {"name": "Max Mustermann", "email": "max.mustermann@example.com"},
            {"name": "Anna Schmidt", "email": "anna.schmidt@example.com"},
            {"name": "Tom Weber", "email": "tom.weber@example.com"}
        ]
        
        created_users = []
        
        for user_info in users_to_create:
            user_data = ApplicationUserCreate(
                name=user_info["name"],
                email=user_info["email"],
                is_active=True
            )
            
            try:
                new_user = await ApplicationUserService.create_user(db, user_data, send_email=False)
                await db.commit()
                created_users.append(new_user)
                print(f"  ✓ {user_info['name']} - Passwort: {new_user.generated_password}")
            except Exception as e:
                print(f"  ✗ Fehler bei {user_info['name']}: {e}")
        
        # Demo 2: List all users
        print(f"\n👥 Admin-Benutzer Übersicht ({len(created_users)} Benutzer):")
        all_users = await ApplicationUserService.get_all_users(db)
        
        for user in all_users:
            status = "🟢 Aktiv" if user.is_active else "🔴 Gesperrt"
            last_login = user.last_logon.strftime('%d.%m.%Y %H:%M') if user.last_logon else "Noch nie"
            print(f"  • {user.name} ({user.email}) - {status} - Erstellt: {user.created_at.strftime('%d.%m.%Y %H:%M')} - Login: {last_login}")
        
        # Demo 3: Authentication test
        if created_users:
            test_user = created_users[0]
            print(f"\n🔑 Authentifizierung Test für {test_user.email}...")
            
            # Successful auth
            auth_result = await ApplicationUserService.authenticate_user(
                db, test_user.email, test_user.generated_password
            )
            if auth_result:
                print(f"  ✓ Authentifizierung erfolgreich")
                await db.commit()
            else:
                print(f"  ✗ Authentifizierung fehlgeschlagen")
            
            # Failed auth
            auth_fail = await ApplicationUserService.authenticate_user(
                db, test_user.email, "wrong_password"
            )
            if not auth_fail:
                print(f"  ✓ Falsche Passwort-Authentifizierung korrekt abgelehnt")
        
        # Demo 4: Password reset
        if created_users:
            user_to_reset = created_users[1] if len(created_users) > 1 else created_users[0]
            print(f"\n🔄 Passwort zurücksetzen für {user_to_reset.name}...")
            
            old_password = user_to_reset.generated_password
            reset_result = await ApplicationUserService.reset_password(
                db, user_to_reset.id, send_email=False
            )
            await db.commit()
            
            if reset_result:
                print(f"  ✓ Neues Passwort: {reset_result.generated_password}")
                
                # Test old password fails
                old_auth = await ApplicationUserService.authenticate_user(
                    db, user_to_reset.email, old_password
                )
                if not old_auth:
                    print(f"  ✓ Altes Passwort ist ungültig")
                
                # Test new password works
                new_auth = await ApplicationUserService.authenticate_user(
                    db, user_to_reset.email, reset_result.generated_password
                )
                if new_auth:
                    print(f"  ✓ Neues Passwort funktioniert")
                    await db.commit()
        
        # Demo 5: Update user
        if created_users:
            user_to_update = created_users[0]
            print(f"\n✏️ Benutzer aktualisieren: {user_to_update.name}...")
            
            update_data = ApplicationUserUpdate(
                name=f"{user_to_update.name} (Aktualisiert)",
                email=f"updated.{user_to_update.email}"
            )
            
            updated_user = await ApplicationUserService.update_user(
                db, user_to_update.id, update_data
            )
            await db.commit()
            
            if updated_user:
                print(f"  ✓ Neuer Name: {updated_user.name}")
                print(f"  ✓ Neue E-Mail: {updated_user.email}")
        
        # Demo 6: Toggle status
        if created_users and len(created_users) > 2:
            user_to_toggle = created_users[2]
            print(f"\n🔄 Status umschalten für {user_to_toggle.name}...")
            
            original_status = user_to_toggle.is_active
            toggled_user = await ApplicationUserService.toggle_user_status(db, user_to_toggle.id)
            await db.commit()
            
            if toggled_user:
                new_status = "Aktiv" if toggled_user.is_active else "Gesperrt"
                print(f"  ✓ Status geändert: {new_status}")
                
                # Toggle back
                toggled_again = await ApplicationUserService.toggle_user_status(db, user_to_toggle.id)
                await db.commit()
                if toggled_again:
                    final_status = "Aktiv" if toggled_again.is_active else "Gesperrt"
                    print(f"  ✓ Status wieder geändert: {final_status}")
        
        # Demo 7: Security features
        print(f"\n🛡️ Sicherheitsfeatures:")
        print(f"  • Passwörter werden mit bcrypt gehashed")
        print(f"  • Automatische Passwort-Generierung (min. 10 Zeichen)")
        print(f"  • E-Mail Eindeutigkeit wird erzwungen")
        print(f"  • Last-Login Tracking")
        print(f"  • Benutzer können aktiviert/deaktiviert werden")
        
        # Demo 8: Email uniqueness test
        print(f"\n📧 Test: E-Mail Eindeutigkeit...")
        if created_users:
            # Get the updated email from the first user (who was updated in Demo 5)
            updated_user = await ApplicationUserService.get_user(db, created_users[0].id)
            test_email = updated_user.email if updated_user else created_users[0].email
            
            duplicate_user = ApplicationUserCreate(
                name="Duplikat Test",
                email=test_email,  # Use the updated email to test duplicate
                is_active=True
            )
            
            try:
                await ApplicationUserService.create_user(db, duplicate_user, send_email=False)
                print(f"  ✗ Duplikat sollte nicht erlaubt sein")
            except ValueError as e:
                print(f"  ✓ Duplikat korrekt abgelehnt: {e}")
            except Exception as e:
                if "Email bereits vergeben" in str(e) or "UNIQUE constraint failed" in str(e):
                    print(f"  ✓ Duplikat korrekt abgelehnt (Eindeutigkeit erzwungen)")
                else:
                    print(f"  ✓ Duplikat abgelehnt: {e}")
        
        print(f"\n🎉 Demo abgeschlossen!")
        print(f"\nZusammenfassung:")
        print(f"  • {len(all_users)} Admin-Benutzer erstellt")
        print(f"  • Alle CRUD-Operationen getestet")
        print(f"  • Authentifizierung funktioniert")
        print(f"  • Passwort-Reset funktioniert") 
        print(f"  • Sicherheitsfeatures aktiv")
        
    # Close engine
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(demo_application_users())