"""
Promote an existing user to admin. Registration always creates a regular "user"
account (there's no public "sign up as admin" — that would be a real security hole),
so the first admin has to be granted some other way. This is that way.

Usage (from backend/):  python -m scripts.make_admin someone@example.com
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.make_admin <email>")
        sys.exit(1)

    email = sys.argv[1]
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"No user found with email {email}. Register the account first, then run this.")
            sys.exit(1)
        user.role = "admin"
        db.commit()
        print(f"{email} is now an admin.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
