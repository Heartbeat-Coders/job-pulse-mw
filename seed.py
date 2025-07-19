# seed_admin.py - Standalone script to create admin user

import asyncio
import sys
import os
from datetime import datetime
from pytz import timezone

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.database import SessionLocal, engine
from app.models import User, Base
import uuid

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_admin_user():
    """Create admin user in the database"""
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Admin user details
        admin_email = "patricia@heartbeatcoders.com"
        admin_password = "recruiter"  # Change this to a secure password
        
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            print(f"Admin user with email {admin_email} already exists!")
            print(f"Admin ID: {existing_admin.id}")
            print(f"Admin Role: {existing_admin.role}")
            return existing_admin
        
        # Create new admin user
        admin_user = User(
            id=uuid.uuid4(),
            first_name="Patricia",
            last_name="Sichali",
            email=admin_email,
            phone="+26599123456",  # Optional
            password=hash_password(admin_password),
            role="recruiter",
            is_active=True,
            created_at=datetime.now(timezone("Africa/Blantyre"))
        )
        
        # Add to database
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"📧 Email: {admin_user.email}")
        print(f"🔑 Password: {admin_password}")
        print(f"👤 Name: {admin_user.first_name} {admin_user.last_name}")
        print(f"🆔 ID: {admin_user.id}")
        print(f"📅 Created: {admin_user.created_at}")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")
        
        return admin_user
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        return None
    finally:
        db.close()

# def create_multiple_admin_users():
#     """Create multiple admin users with different details"""
    
#     Base.metadata.create_all(bind=engine)
#     db = SessionLocal()
    
#     admin_users = [
#         {
#             "first_name": "John",
#             "last_name": "Doe",
#             "email": "john.admin@heartbeatcoders.com",
#             "phone": "+265888111111",
#             "password": "admin123"
#         },
#         {
#             "first_name": "Jane",
#             "last_name": "Smith",
#             "email": "jane.admin@heartbeatcoders.com", 
#             "phone": "+265888222222",
#             "password": "admin456"
#         },
#         {
#             "first_name": "Super",
#             "last_name": "Admin",
#             "email": "superadmin@heartbeatcoders.com",
#             "phone": "+265888000000",
#             "password": "superadmin123"
#         }
#     ]
    
#     try:
#         created_users = []
        
#         for admin_data in admin_users:
#             # Check if user already exists
#             existing_user = db.query(User).filter(User.email == admin_data["email"]).first()
#             if existing_user:
#                 print(f"⚠️  User with email {admin_data['email']} already exists, skipping...")
#                 continue
            
#             # Create new admin user
#             admin_user = User(
#                 id=uuid.uuid4(),
#                 first_name=admin_data["first_name"],
#                 last_name=admin_data["last_name"],
#                 email=admin_data["email"],
#                 phone=admin_data["phone"],
#                 password=hash_password(admin_data["password"]),
#                 role="admin",
#                 is_active=True,
#                 created_at=datetime.now(timezone("Africa/Blantyre"))
#             )
            
#             db.add(admin_user)
#             created_users.append({
#                 "user": admin_user,
#                 "password": admin_data["password"]
#             })
        
#         db.commit()
        
#         print(f"✅ Created {len(created_users)} admin users successfully!")
#         print("\n" + "="*50)
        
#         for user_data in created_users:
#             user = user_data["user"]
#             password = user_data["password"]
#             print(f"👤 {user.first_name} {user.last_name}")
#             print(f"📧 Email: {user.email}")
#             print(f"🔑 Password: {password}")
#             print(f"📱 Phone: {user.phone}")
#             print(f"🆔 ID: {user.id}")
#             print("-" * 30)
        
#         print("\n⚠️  IMPORTANT: Change default passwords after first login!")
        
#     except Exception as e:
#         db.rollback()
#         print(f"❌ Error creating admin users: {str(e)}")
#     finally:
#         db.close()




def list_all_users():
    """List all users in the database"""
    
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"📊 Total Users: {len(users)}")
        print("=" * 80)
        
        for user in users:
            status = "🟢 Active" if user.is_active else "🔴 Inactive"
            role_emoji = {"admin": "👑", "recruiter": "💼", "applicant": "👤"}.get(user.role, "❓")
            
            print(f"{role_emoji} {user.first_name} {user.last_name}")
            print(f"   📧 {user.email}")
            print(f"   🏷️  Role: {user.role.upper()}")
            print(f"   📊 Status: {status}")
            print(f"   📅 Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   🆔 ID: {user.id}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")
    finally:
        db.close()

def reset_admin_password(admin_email: str, new_password: str):
    """Reset admin password"""
    
    db = SessionLocal()
    try:
        admin = db.query(User).filter(
            User.email == admin_email,
            User.role == "admin"
        ).first()
        
        if not admin:
            print(f"❌ Admin user with email {admin_email} not found!")
            return False
        
        admin.password = hash_password(new_password)
        db.commit()
        
        print(f"✅ Password reset successfully for {admin.first_name} {admin.last_name}")
        print(f"📧 Email: {admin.email}")
        print(f"🔑 New Password: {new_password}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error resetting password: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Heartbeat Coders Admin User Setup")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "create":
            create_admin_user()
        # elif command == "multiple":
        #     create_multiple_admin_users()
        elif command == "list":
            list_all_users()
        elif command == "reset" and len(sys.argv) == 4:
            email = sys.argv[2]
            password = sys.argv[3]
            reset_admin_password(email, password)
        else:
            print("Usage:")
            print("  python seed_admin.py create          # Create single admin")
            print("  python seed_admin.py multiple        # Create multiple admins") 
            print("  python seed_admin.py list            # List all users")
            print("  python seed_admin.py reset <email> <new_password>  # Reset password")
    else:
        # Default: create single admin
        create_admin_user()