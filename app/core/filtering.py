"""Reusable filtering utilities for list endpoints."""

from datetime import datetime
from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query


class FilterSpec:
    def __init__(
        self,
        query: Query,
        sort: str | None = None,
        direction: str = "asc",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        **filters: Any,
    ):
        self.query = query
        self._apply_filters(filters)
        self._apply_date_range(start_date, end_date)
        self._apply_sort(sort, direction)

    def _apply_filters(self, filters: dict[str, Any]):
        for key, value in filters.items():
            if value is None:
                continue
            column = getattr(self.query.column_descriptions[0]["entity"], key, None)
            if column is not None:
                self.query = self.query.filter(column == value)

    def _apply_date_range(self, start_date: datetime | None, end_date: datetime | None):
        if start_date is not None:
            self.query = self.query.filter(
                self.query.column_descriptions[0]["entity"].created_at >= start_date
            )
        if end_date is not None:
            self.query = self.query.filter(
                self.query.column_descriptions[0]["entity"].created_at <= end_date
            )

    def _apply_sort(self, sort: str | None, direction: str):
        if not sort:
            return
        column = getattr(self.query.column_descriptions[0]["entity"], sort, None)
        if column is not None:
            order = asc if direction.lower() == "asc" else desc
            self.query = self.query.order_by(order(column))

    def get_query(self) -> Query:
        return self.query
