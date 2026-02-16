#!/usr/bin/env python3
"""CLI tool for managing users and secrets."""

import argparse
import secrets
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.enums import UserRole
from app.models import User
from app.services.auth import create_user, get_password_hash, get_user_by_email


def create_admin_user(db: Session, email: str, username: str, password: str) -> None:
    """Create an admin user."""
    existing = get_user_by_email(db, email)
    if existing:
        print(f"ERROR: User with email {email} already exists")
        sys.exit(1)

    user = create_user(db, email, username, password, UserRole.ADMIN)
    print(f"✅ Admin user created: {user.email} (ID: {user.id})")


def create_regular_user(db: Session, email: str, username: str, password: str) -> None:
    """Create a regular user."""
    existing = get_user_by_email(db, email)
    if existing:
        print(f"ERROR: User with email {email} already exists")
        sys.exit(1)

    user = create_user(db, email, username, password, UserRole.USER)
    print(f"✅ User created: {user.email} (ID: {user.id})")


def list_users(db: Session) -> None:
    """List all users."""
    users = db.query(User).all()
    if not users:
        print("No users found")
        return

    print(f"\n{'ID':<5} {'Email':<30} {'Username':<20} {'Role':<10} {'Active':<8}")
    print("-" * 80)
    for user in users:
        print(
            f"{user.id:<5} {user.email:<30} {user.username:<20} {user.role:<10} {'Yes' if user.is_active else 'No':<8}"
        )
    print()


def reset_password(db: Session, email: str, new_password: str) -> None:
    """Reset a user's password."""
    user = get_user_by_email(db, email)
    if not user:
        print(f"ERROR: User with email {email} not found")
        sys.exit(1)

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    print(f"✅ Password reset for {user.email}")


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret."""
    return secrets.token_urlsafe(64)


def rotate_secrets() -> None:
    """Generate new secrets for .env file."""
    print("\n🔑 Generate new secrets for .env file:")
    print(f"\nAPI_KEY={generate_api_key()}")
    print(f"JWT_SECRET_KEY={generate_jwt_secret()}")
    print(f"SCRAPER_PRO_HMAC_SECRET={generate_api_key()}")
    print("\n⚠️  Copy these to your .env file and restart the application\n")


def main():
    parser = argparse.ArgumentParser(description="Manage Email Engine users and secrets")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # create-admin
    create_admin_parser = subparsers.add_parser("create-admin", help="Create admin user")
    create_admin_parser.add_argument("--email", required=True, help="User email")
    create_admin_parser.add_argument("--username", required=True, help="Username")
    create_admin_parser.add_argument("--password", required=True, help="Password")

    # create-user
    create_user_parser = subparsers.add_parser("create-user", help="Create regular user")
    create_user_parser.add_argument("--email", required=True, help="User email")
    create_user_parser.add_argument("--username", required=True, help="Username")
    create_user_parser.add_argument("--password", required=True, help="Password")

    # list
    subparsers.add_parser("list", help="List all users")

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("--email", required=True, help="User email")
    reset_parser.add_argument("--password", required=True, help="New password")

    # rotate-secrets
    subparsers.add_parser("rotate-secrets", help="Generate new secrets")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Commands that don't need DB
    if args.command == "rotate-secrets":
        rotate_secrets()
        return

    # Commands that need DB
    db = SessionLocal()
    try:
        if args.command == "create-admin":
            create_admin_user(db, args.email, args.username, args.password)
        elif args.command == "create-user":
            create_regular_user(db, args.email, args.username, args.password)
        elif args.command == "list":
            list_users(db)
        elif args.command == "reset-password":
            reset_password(db, args.email, args.password)
    finally:
        db.close()


if __name__ == "__main__":
    main()
