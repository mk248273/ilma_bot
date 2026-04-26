"""
Seed script to create initial admin user.
Run this after deployment to set up the first admin account.
"""
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import SessionLocal, User, DATA_DIR
from backend.auth import get_password_hash


def create_admin_user():
    """Create admin user from environment variables"""
    db = SessionLocal()
    
    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@ilma.edu.pk")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")
        
        # Check if admin already exists
        existing = db.query(User).filter(User.username == admin_username).first()
        if existing:
            print(f"Admin user '{admin_username}' already exists.")
            # Ensure admin status
            if not existing.is_admin:
                existing.is_admin = True
                db.commit()
                print(f"Updated '{admin_username}' to admin status.")
            return
        
        # Check email collision
        existing_email = db.query(User).filter(User.email == admin_email).first()
        if existing_email:
            print(f"Warning: Email '{admin_email}' already in use by user '{existing_email.username}'")
            print("Admin user not created. Please set a different ADMIN_EMAIL.")
            return
        
        # Create admin user
        admin = User(
            username=admin_username,
            email=admin_email,
            full_name=admin_full_name,
            student_id="ADMIN001",
            department="IT",
            semester="N/A",
            hashed_password=get_password_hash(admin_password),
            is_admin=True,
            created_at=datetime.utcnow(),
            last_login=None,
            profile_image=None
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print(f"✓ Admin user created successfully!")
        print(f"  Username: {admin_username}")
        print(f"  Email: {admin_email}")
        print(f"  Password: {'*' * len(admin_password)}")
        print(f"  Database: {os.path.join(DATA_DIR, 'ilma_bot_v2.db')}")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("ILMA Bot - Admin Seeder")
    print("=" * 40)
    create_admin_user()
