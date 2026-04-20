from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T


class CollectionData(BaseModel, Generic[T]):
    items: list[T]
    total: int


class PaginatedData(CollectionData[T], Generic[T]):
    page: int
    page_size: int
    total_pages: int
