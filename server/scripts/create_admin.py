from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main() -> None:
    settings = get_settings()
    username = "admin"
    password = "admin123456"

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.username == username))
        if existing:
            return
        user = User(
            username=username,
            password_hash=hash_password(password),
            display_name="Outlawer Admin",
            status="active",
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
