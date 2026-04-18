from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = 20


def normalize_page_params(page: int = 1, page_size: int = 20, *, max_page_size: int = 100) -> PageParams:
    safe_page = max(page, 1)
    safe_page_size = max(1, min(page_size, max_page_size))
    return PageParams(page=safe_page, page_size=safe_page_size)


def paginate_query(db: Session, query: Select, params: PageParams) -> tuple[list, int]:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = int(db.scalar(count_query) or 0)
    items = db.scalars(
        query.limit(params.page_size).offset((params.page - 1) * params.page_size)
    ).all()
    return items, total
