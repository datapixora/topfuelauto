import os
import sys

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User


def main():
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD must be set; no changes made.")
        return

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            if not user.is_admin:
                user.is_admin = True
                db.add(user)
                db.commit()
                print(f"User {email} exists; marked as admin.")
            else:
                print(f"User {email} already admin; no changes.")
            return

        # create new admin
        user = User(email=email, password_hash=get_password_hash(password), is_admin=True)
        db.add(user)
        db.commit()
        print(f"Created admin user {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()