"""Create initial admin user from env vars."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password


def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.admin_email).first()
        if existing:
            print(f"Admin user {settings.admin_email} already exists.")
            return

        user = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {settings.admin_email}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
