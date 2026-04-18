import sys
import time

from sqlalchemy import text

from app.core.database import engine


def main() -> int:
    for _ in range(60):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return 0
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return 1


if __name__ == "__main__":
    sys.exit(main())
