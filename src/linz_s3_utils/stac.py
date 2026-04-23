from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import pystac
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO
from shapely.geometry import box, shape


DEFAULT_PAGE_SIZE = 100


def _collection_extra_fields(item: pystac.Item) -> dict[str, Any]:
    collection = item.get_collection()
    return {} if collection is None else dict(collection.extra_fields)


def _item_value(item: pystac.Item, field: str) -> Any:
    if field.startswith("properties."):
        current: Any = item.properties
        for part in field.removeprefix("properties.").split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    if field == "collection":
        return item.collection_id or item.to_dict().get("collection")

    if field in {"id", "bbox", "geometry"}:
        return getattr(item, field, None)

    if field in item.properties:
        return item.properties[field]

    return _collection_extra_fields(item).get(field)


def _item_geometry(item: pystac.Item) -> Any:
    if item.geometry:
        return shape(item.geometry)
    if item.bbox:
        return box(*item.bbox)
    return None


def _parse_datetime_range(value: Any) -> tuple[datetime | None, datetime | None]:
    normalized = ItemSearch(url="memory://noop", stac_io=StacApiIO(), datetime=value)
    raw = normalized.get_parameters().get("datetime")
    if raw is None:
        return None, None
    if "/" not in raw:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed, parsed
    start_raw, end_raw = raw.split("/", maxsplit=1)
    start = (
        None
        if start_raw == ".."
        else datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    )
    end = (
        None
        if end_raw == ".."
        else datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
    )
    return start, end


class CatalogSearchIO(StacApiIO):
    def __init__(self, catalog: pystac.Catalog) -> None:
        super().__init__()
        self.catalog = catalog

    def _matches_ids(self, item: pystac.Item, parameters: dict[str, Any]) -> bool:
        ids = parameters.get("ids")
        return True if not ids else item.id in ids

    def _matches_collections(self, item: pystac.Item, parameters: dict[str, Any]) -> bool:
        collections = parameters.get("collections")
        return True if not collections else item.collection_id in collections

    def _matches_bbox(self, item: pystac.Item, parameters: dict[str, Any]) -> bool:
        search_bbox = parameters.get("bbox")
        if not search_bbox:
            return True
        geometry = _item_geometry(item)
        return False if geometry is None else geometry.intersects(box(*search_bbox))

    def _matches_datetime(self, item: pystac.Item, parameters: dict[str, Any]) -> bool:
        search_datetime = parameters.get("datetime")
        if not search_datetime:
            return True
        item_dt = item.datetime
        if item_dt is None:
            return False
        if item_dt.tzinfo is None:
            item_dt = item_dt.replace(tzinfo=timezone.utc)
        start, end = _parse_datetime_range(search_datetime)
        if start and item_dt < start:
            return False
        if end and item_dt > end:
            return False
        return True

    def _matches_query(self, item: pystac.Item, parameters: dict[str, Any]) -> bool:
        query = parameters.get("query")
        if not query:
            return True

        for field, operations in query.items():
            item_value = _item_value(item, field)
            for op, expected in operations.items():
                if op == "eq" and item_value != expected:
                    return False
                if op == "neq" and item_value == expected:
                    return False
                if op == "lt" and not (item_value is not None and item_value < expected):
                    return False
                if op == "lte" and not (
                    item_value is not None and item_value <= expected
                ):
                    return False
                if op == "gt" and not (item_value is not None and item_value > expected):
                    return False
                if op == "gte" and not (
                    item_value is not None and item_value >= expected
                ):
                    return False
                if op == "in" and item_value not in expected:
                    return False
        return True

    def _matches(self, item: pystac.Item, parameters: dict[str, Any]) -> bool:
        return (
            self._matches_ids(item, parameters)
            and self._matches_collections(item, parameters)
            and self._matches_bbox(item, parameters)
            and self._matches_datetime(item, parameters)
            and self._matches_query(item, parameters)
        )

    def _iter_item_dicts(
        self,
        parameters: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        params = parameters or {}
        for item in self.catalog.get_items(recursive=True):
            if self._matches(item, params):
                yield item.to_dict()

    def _page_size(self, parameters: dict[str, Any] | None) -> int:
        if not parameters:
            return DEFAULT_PAGE_SIZE
        limit = parameters.get("limit")
        return DEFAULT_PAGE_SIZE if limit is None else int(limit)

    def _feature_collection(
        self,
        features: list[dict[str, Any]],
        matched: int,
    ) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": features,
            "numberMatched": matched,
            "numberReturned": len(features),
        }

    def get_pages(
        self,
        url: str,
        method: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        matched_items = list(self._iter_item_dicts(parameters))
        page_size = self._page_size(parameters)
        matched = len(matched_items)

        for offset in range(0, matched, page_size):
            features = matched_items[offset : offset + page_size]
            if features:
                yield self._feature_collection(features, matched)

    def read_json(
        self,
        source: str,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        parameters = kwargs.get("parameters")
        matched_items = list(self._iter_item_dicts(parameters))
        page_size = self._page_size(parameters)
        return self._feature_collection(matched_items[:page_size], len(matched_items))


def search(catalog: pystac.Catalog, **search_kwargs: Any) -> ItemSearch:
    return ItemSearch(
        url="memory://catalog-search",
        stac_io=CatalogSearchIO(catalog),
        client=None,
        **search_kwargs,
    )
