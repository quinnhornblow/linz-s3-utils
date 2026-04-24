from calendar import monthrange
from collections.abc import Iterable, Iterator
from datetime import date, time, timezone
from datetime import datetime as DateTime
from pathlib import Path
from typing import List
from warnings import filterwarnings

import requests_cache
from pystac import Collection, Item
from pystac.utils import str_to_datetime
from pystac_client import Client
from pystac_client.item_search import (
    BBoxLike,
    DatetimeLike,
    IntersectsLike,
)
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import NoConformsTo
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry

filterwarnings(
    "ignore",
    category=NoConformsTo,
    module=r"pystac_client\.client",
)


stac_io = StacApiIO()
cache_file = Path(__file__).parent / "stac_cache.sqlite"
stac_io.session = requests_cache.CachedSession(
    cache_name=str(cache_file),
    expire_after=3600,
)


class StacCatalogClient:
    """Client for searching STAC catalogs that do not expose item search."""

    def __init__(self, catalog_url: str):
        """Open a STAC catalog from a URL."""
        self.client = Client.open(
            catalog_url,
            stac_io=stac_io,
        )

    def search(
        self,
        *,
        ids: str | Iterable[str] | None = None,
        collections: str | Iterable[str | Collection] | Collection | None = None,
        bbox: BBoxLike | None = None,
        intersects: IntersectsLike | None = None,
        datetime: DatetimeLike | None = None,
        gsd: int | None = None,
        linz_filters: dict | None = None,
        sortby: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Item]:
        """Search catalog collections and items with local filter logic."""
        catalog_collections = self.client.get_collections()

        filtered_collections = _filter_collections(
            catalog_collections,
            collections=collections,
            bbox=bbox,
            intersects=intersects,
            datetime=datetime,
            gsd=gsd,
            **(linz_filters or {}),
        )

        items = (
            item
            for collection in filtered_collections
            for item in _filter_items(
                collection.get_items(),
                ids=ids,
                bbox=bbox,
                intersects=intersects,
                datetime=datetime,
            )
        )

        if sortby:
            items = iter(sorted(items, key=lambda item: _item_sort_value(item, sortby)))

        for count, item in enumerate(items):
            if max_items is not None and count >= max_items:
                break
            yield item


def _filter_collections(
    catalog_collections: Iterable[Collection],
    collections: str | Iterable[str | Collection] | Collection | None = None,
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
    gsd: int | None = None,
    **kwargs,
) -> List[Collection]:
    filtered_collections = []
    bbox_geometry = _geometry_from_bbox(bbox)
    intersects_geometry = _geometry_from_intersects(intersects)
    datetime_interval = _parse_datetime_interval(datetime)
    collection_ids = _collection_ids(collections)

    for collection in catalog_collections:
        if collection_ids is not None and collection.id not in collection_ids:
            continue

        if gsd is not None and collection.extra_fields.get("gsd") != gsd:
            continue

        if datetime_interval and not _collection_overlaps_datetime(
            collection,
            datetime_interval,
        ):
            continue

        collection_geometry = _geometry_from_bbox(collection.extent.spatial.bboxes[0])
        if bbox_geometry and not collection_geometry.intersects(bbox_geometry):
            continue
        if intersects_geometry and not collection_geometry.intersects(
            intersects_geometry
        ):
            continue

        if not _matches_extra_fields(collection, kwargs):
            continue

        filtered_collections.append(collection)
    return filtered_collections


def _filter_items(
    items: Iterable[Item],
    ids: str | Iterable[str] | None = None,
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
) -> Iterator[Item]:
    bbox_geometry = _geometry_from_bbox(bbox)
    intersects_geometry = _geometry_from_intersects(intersects)
    datetime_interval = _parse_datetime_interval(datetime)
    item_ids = _ids(ids)

    for item in items:
        if item_ids is not None and item.id not in item_ids:
            continue

        item_geometry = shape(item.geometry) if item.geometry else None

        if bbox_geometry and (
            item_geometry is None or not item_geometry.intersects(bbox_geometry)
        ):
            continue
        if intersects_geometry and (
            item_geometry is None or not item_geometry.intersects(intersects_geometry)
        ):
            continue
        item_datetime_interval = _item_datetime_interval(item)
        if (
            datetime_interval
            and item_datetime_interval
            and not _intervals_overlap(
                item_datetime_interval,
                datetime_interval,
            )
        ):
            continue
        yield item


def _matches_extra_fields(collection: Collection, filters: dict) -> bool:
    for key, value in filters.items():
        if key.startswith("linz_"):
            key = key.replace("linz_", "linz:", 1)
        if collection.extra_fields.get(key) != value:
            return False
    return True


def _ids(values: str | Iterable[str] | None) -> set[str] | None:
    if values is None:
        return None
    if isinstance(values, str):
        return {values}
    return set(values)


def _collection_ids(
    values: str | Iterable[str | Collection] | Collection | None,
) -> set[str] | None:
    if values is None:
        return None
    if isinstance(values, Collection):
        return {values.id}
    if isinstance(values, str):
        return {values}
    return {value.id if isinstance(value, Collection) else value for value in values}


def _geometry_from_bbox(
    bbox_value: BBoxLike | BaseGeometry | None,
) -> BaseGeometry | None:
    if bbox_value is None:
        return None
    if isinstance(bbox_value, BaseGeometry):
        return bbox_value
    return box(*bbox_value)


def _geometry_from_intersects(
    intersects: IntersectsLike | BaseGeometry | None,
) -> BaseGeometry | None:
    if intersects is None:
        return None
    if isinstance(intersects, BaseGeometry):
        return intersects
    if hasattr(intersects, "__geo_interface__"):
        return shape(intersects.__geo_interface__)
    return shape(intersects)


def _parse_datetime_interval(
    datetime_value: DatetimeLike | None,
) -> tuple[DateTime | None, DateTime | None] | None:
    if datetime_value is None:
        return None

    if isinstance(datetime_value, str):
        if "/" in datetime_value:
            start, end = datetime_value.split("/", 1)
            return _parse_datetime_bound(start), _parse_datetime_bound(end, is_end=True)
        return _parse_datetime_bound(datetime_value), _parse_datetime_bound(
            datetime_value,
            is_end=True,
        )

    if isinstance(datetime_value, (list, tuple)):
        start, end = datetime_value
        return _parse_datetime_bound(start), _parse_datetime_bound(end, is_end=True)

    instant = _normalize_datetime(datetime_value)
    return instant, instant


def _parse_datetime_bound(
    value: DateTime | date | str | None,
    *,
    is_end: bool = False,
) -> DateTime | None:
    if value is None or value in ("", ".."):
        return None
    if not isinstance(value, str):
        return _normalize_datetime(value)
    if isinstance(value, str) and "T" not in value:
        expanded = _expand_simple_date(value)
        if expanded:
            return expanded[1] if is_end else expanded[0]
    return _normalize_datetime(str_to_datetime(value))


def _expand_simple_date(value: str) -> tuple[DateTime, DateTime] | None:
    parts = value.split("-")
    if len(parts) == 1 and len(parts[0]) == 4:
        year = int(parts[0])
        return (
            DateTime(year, 1, 1),
            DateTime(year, 12, 31, 23, 59, 59, 999999),
        )
    if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2:
        year = int(parts[0])
        month = int(parts[1])
        last_day = monthrange(year, month)[1]
        return (
            DateTime(year, month, 1),
            DateTime(year, month, last_day, 23, 59, 59, 999999),
        )
    if (
        len(parts) == 3
        and len(parts[0]) == 4
        and len(parts[1]) == 2
        and len(parts[2]) == 2
    ):
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        return (
            DateTime(year, month, day),
            DateTime(year, month, day, 23, 59, 59, 999999),
        )
    return None


def _normalize_datetime(value: DateTime | date | None) -> DateTime | None:
    if value is None:
        return None
    if isinstance(value, DateTime):
        dt = value
    else:
        dt = DateTime.combine(value, time.min)
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _collection_overlaps_datetime(
    collection: Collection,
    datetime_interval: tuple[DateTime | None, DateTime | None],
) -> bool:
    if not collection.extent.temporal:
        return False

    for start, end in collection.extent.temporal.intervals:
        collection_interval = (_normalize_datetime(start), _normalize_datetime(end))
        if _intervals_overlap(collection_interval, datetime_interval):
            return True

    return False


def _item_datetime_interval(
    item: Item,
) -> tuple[DateTime | None, DateTime | None] | None:
    if item.datetime:
        instant = _normalize_datetime(item.datetime)
        return instant, instant

    start = item.properties.get("start_datetime")
    end = item.properties.get("end_datetime")
    if not start and not end:
        return None

    return _parse_datetime_bound(str(start)) if start else None, _parse_datetime_bound(
        str(end)
    ) if end else None


def _intervals_overlap(
    left: tuple[DateTime | None, DateTime | None],
    right: tuple[DateTime | None, DateTime | None],
) -> bool:
    left_start, left_end = left
    right_start, right_end = right

    starts_before_right_ends = (
        right_end is None or left_start is None or left_start <= right_end
    )
    ends_after_right_starts = (
        right_start is None or left_end is None or left_end >= right_start
    )
    return starts_before_right_ends and ends_after_right_starts


def _item_sort_value(item: Item, sortby: str):
    reverse = sortby.startswith("-")
    field_name = sortby[1:] if reverse else sortby
    value = getattr(item, field_name, None)
    if value is None:
        value = item.properties.get(field_name)
    if field_name == "datetime":
        value = _normalize_datetime(value)
    return (value is None, value if not reverse else _reverse_sort_value(value))


def _reverse_sort_value(value):
    if isinstance(value, DateTime):
        return -value.timestamp()
    if isinstance(value, (int, float)):
        return -value
    return value
