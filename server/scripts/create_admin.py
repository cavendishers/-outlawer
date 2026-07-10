from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main() -> None:
    settings = get_settings()
    username = settings.bootstrap_admin_username
    password = settings.bootstrap_admin_password
    if not username or not password:
        if settings.environment.lower() == "production":
            raise RuntimeError("Bootstrap admin credentials are required in production")
        print("Bootstrap admin is not configured; skipping admin creation.")
        return
    if settings.environment.lower() == "production" and len(password) < 12:
        raise RuntimeError("Bootstrap admin password must contain at least 12 characters in production")

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.username == username))
        if existing:
            return
        user = User(
            username=username,
            password_hash=hash_password(password),
            display_name=settings.bootstrap_admin_display_name,
            status="active",
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
