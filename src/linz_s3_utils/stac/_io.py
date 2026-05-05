from calendar import monthrange
from collections.abc import Iterable, Iterator
from datetime import date, time, timezone
from datetime import datetime as DateTime
from pathlib import Path
from warnings import filterwarnings

import requests_cache
from pystac import Collection, Item
from pystac.utils import str_to_datetime
from pystac_client import Client
from pystac_client.item_search import BBoxLike, DatetimeLike, IntersectsLike
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
    """Search a STAC catalog with simple local filtering."""

    def __init__(self, catalog_url: str):
        self.client = Client.open(catalog_url, stac_io=stac_io)

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
        matching_items: list[Item] = []

        for collection in self.client.get_collections():
            if not collection_matches(
                collection,
                collections=collections,
                bbox=bbox,
                intersects=intersects,
                datetime=datetime,
                gsd=gsd,
                filters=linz_filters or {},
            ):
                continue

            for item in collection.get_items():
                if item_matches(
                    item,
                    ids=ids,
                    bbox=bbox,
                    intersects=intersects,
                    datetime=datetime,
                ):
                    matching_items.append(item)

        if sortby:
            matching_items.sort(key=lambda item: item_sort_value(item, sortby))

        if max_items is not None:
            matching_items = matching_items[:max_items]

        return iter(matching_items)


def _filter_collections(
    catalog_collections: Iterable[Collection],
    collections: str | Iterable[str | Collection] | Collection | None = None,
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
    gsd: int | None = None,
    **kwargs,
) -> list[Collection]:
    return [
        collection
        for collection in catalog_collections
        if collection_matches(
            collection,
            collections=collections,
            bbox=bbox,
            intersects=intersects,
            datetime=datetime,
            gsd=gsd,
            filters=kwargs,
        )
    ]


def _filter_items(
    items: Iterable[Item],
    ids: str | Iterable[str] | None = None,
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
) -> Iterator[Item]:
    return iter(
        [
            item
            for item in items
            if item_matches(
                item,
                ids=ids,
                bbox=bbox,
                intersects=intersects,
                datetime=datetime,
            )
        ]
    )


def collection_matches(
    collection: Collection,
    *,
    collections: str | Iterable[str | Collection] | Collection | None,
    bbox: BBoxLike | None,
    intersects: IntersectsLike | None,
    datetime: DatetimeLike | None,
    gsd: int | None,
    filters: dict,
) -> bool:
    requested_collection_ids = normalize_collection_ids(collections)
    if (
        requested_collection_ids is not None
        and collection.id not in requested_collection_ids
    ):
        return False

    if gsd is not None and collection.extra_fields.get("gsd") != gsd:
        return False

    if not collection_matches_filters(collection, filters):
        return False

    search_range = make_datetime_range(datetime)
    if search_range is not None and not collection_overlaps_datetime(collection, search_range):
        return False

    collection_geometry = make_geometry(collection.extent.spatial.bboxes[0], from_bbox=True)
    bbox_geometry = make_geometry(bbox, from_bbox=True)
    intersects_geometry = make_geometry(intersects)

    if bbox_geometry is not None and not collection_geometry.intersects(bbox_geometry):
        return False
    if (
        intersects_geometry is not None
        and not collection_geometry.intersects(intersects_geometry)
    ):
        return False

    return True


def item_matches(
    item: Item,
    *,
    ids: str | Iterable[str] | None,
    bbox: BBoxLike | None,
    intersects: IntersectsLike | None,
    datetime: DatetimeLike | None,
) -> bool:
    requested_ids = normalize_ids(ids)
    if requested_ids is not None and item.id not in requested_ids:
        return False

    item_geometry = shape(item.geometry) if item.geometry else None
    bbox_geometry = make_geometry(bbox, from_bbox=True)
    intersects_geometry = make_geometry(intersects)

    if bbox_geometry is not None and (
        item_geometry is None or not item_geometry.intersects(bbox_geometry)
    ):
        return False
    if intersects_geometry is not None and (
        item_geometry is None or not item_geometry.intersects(intersects_geometry)
    ):
        return False

    search_range = make_datetime_range(datetime)
    item_range = item_datetime_range(item)
    if (
        search_range is not None
        and item_range is not None
        and not ranges_overlap(item_range, search_range)
    ):
        return False

    return True


def collection_matches_filters(collection: Collection, filters: dict) -> bool:
    for key, value in filters.items():
        if key.startswith("linz_"):
            key = key.replace("linz_", "linz:", 1)
        if collection.extra_fields.get(key) != value:
            return False
    return True


def normalize_ids(values: str | Iterable[str] | None) -> set[str] | None:
    if values is None:
        return None
    if isinstance(values, str):
        return {values}
    return set(values)


def normalize_collection_ids(
    values: str | Iterable[str | Collection] | Collection | None,
) -> set[str] | None:
    if values is None:
        return None
    if isinstance(values, Collection):
        return {values.id}
    if isinstance(values, str):
        return {values}
    return {value.id if isinstance(value, Collection) else value for value in values}


def make_geometry(
    value: BBoxLike | IntersectsLike | BaseGeometry | None,
    *,
    from_bbox: bool = False,
) -> BaseGeometry | None:
    if value is None:
        return None
    if isinstance(value, BaseGeometry):
        return value
    if from_bbox:
        return box(*value)
    if hasattr(value, "__geo_interface__"):
        return shape(value.__geo_interface__)
    return shape(value)


def make_datetime_range(
    datetime_value: DatetimeLike | None,
) -> tuple[DateTime | None, DateTime | None] | None:
    if datetime_value is None:
        return None

    if isinstance(datetime_value, str):
        if "/" in datetime_value:
            start, end = datetime_value.split("/", 1)
            return parse_datetime_bound(start), parse_datetime_bound(end, is_end=True)
        return parse_datetime_bound(datetime_value), parse_datetime_bound(
            datetime_value,
            is_end=True,
        )

    if isinstance(datetime_value, (list, tuple)):
        start, end = datetime_value
        return parse_datetime_bound(start), parse_datetime_bound(end, is_end=True)

    instant = normalize_datetime(datetime_value)
    return instant, instant


def parse_datetime_bound(
    value: DateTime | date | str | None,
    *,
    is_end: bool = False,
) -> DateTime | None:
    if value is None or value in ("", ".."):
        return None
    if not isinstance(value, str):
        return normalize_datetime(value)
    if "T" not in value:
        expanded = expand_simple_date(value)
        if expanded:
            return expanded[1] if is_end else expanded[0]
    return normalize_datetime(str_to_datetime(value))


def expand_simple_date(value: str) -> tuple[DateTime, DateTime] | None:
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


def normalize_datetime(value: DateTime | date | None) -> DateTime | None:
    if value is None:
        return None
    if isinstance(value, DateTime):
        normalized = value
    else:
        normalized = DateTime.combine(value, time.min)
    if normalized.tzinfo:
        return normalized.astimezone(timezone.utc).replace(tzinfo=None)
    return normalized


def collection_overlaps_datetime(
    collection: Collection,
    search_range: tuple[DateTime | None, DateTime | None],
) -> bool:
    if not collection.extent.temporal:
        return False

    for start, end in collection.extent.temporal.intervals:
        collection_range = (normalize_datetime(start), normalize_datetime(end))
        if ranges_overlap(collection_range, search_range):
            return True
    return False


def item_datetime_range(item: Item) -> tuple[DateTime | None, DateTime | None] | None:
    if item.datetime:
        instant = normalize_datetime(item.datetime)
        return instant, instant

    start = item.properties.get("start_datetime")
    end = item.properties.get("end_datetime")
    if not start and not end:
        return None

    start_value = parse_datetime_bound(str(start)) if start else None
    end_value = parse_datetime_bound(str(end)) if end else None
    return start_value, end_value


def ranges_overlap(
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


def item_sort_value(item: Item, sortby: str):
    reverse = sortby.startswith("-")
    field_name = sortby[1:] if reverse else sortby
    value = getattr(item, field_name, None)
    if value is None:
        value = item.properties.get(field_name)
    if field_name == "datetime":
        value = normalize_datetime(value)
    return (value is None, value if not reverse else reverse_sort_value(value))


def reverse_sort_value(value):
    if isinstance(value, DateTime):
        return -value.timestamp()
    if isinstance(value, (int, float)):
        return -value
    return value
