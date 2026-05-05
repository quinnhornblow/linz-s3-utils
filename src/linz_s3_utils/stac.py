from collections.abc import Iterator
from datetime import UTC, datetime
from enum import Enum
from itertools import chain, islice
from pathlib import Path
from typing import Any, Literal
from warnings import filterwarnings

import odc.stac
import requests_cache
import xarray as xr
from pystac import Collection
from pystac.item import Item
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import FallbackToPystac, NoConformsTo

filterwarnings(
    "ignore",
    category=NoConformsTo,
    module=r"pystac_client\.client",
)
filterwarnings(
    "ignore", category=FallbackToPystac, module=r"pystac_client\.collection_client"
)


class CatalogURLs(Enum):
    """Enumeration of STAC catalog URLs."""

    ELEVATION = "https://nz-elevation.s3-ap-southeast-2.amazonaws.com/catalog.json"


stac_io = StacApiIO()
cache_file = Path(__file__).parent / "stac_cache.sqlite"
stac_io.session = requests_cache.CachedSession(
    cache_name=str(cache_file),
    expire_after=3600,
)


class StacCatalogClient:
    """Search a STAC catalog with simple local filtering."""

    def __init__(self, catalog: Literal["elevation"] = "elevation"):
        """Create a STAC client for the selected catalog."""
        self.client = Client.open(CatalogURLs[catalog.upper()].value, stac_io=stac_io)

    def search(
        self,
        collections: list[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
        ids: list[str] | None = None,
        bbox: list[float] | None = None,
        intersects: object | None = None,
        datetime: str | None = None,
        limit: int | None = None,
        query: object | None = None,
        filter: object | None = None,
        sortby: object | None = None,
        fields: object | None = None,
    ) -> Iterator[Item]:
        """Mimic `pystac_client.Client.search` on a STAC catalog."""
        self._raise_if_unsupported(
            query=query,
            filter=filter,
            sortby=sortby,
            fields=fields,
        )
        ids_filter = set(ids) if ids is not None else None
        bbox_filter = self._get_xy_bbox(bbox) if bbox is not None else None
        intersects_filter = (
            self._xy_bbox_from_geojson_geometry(intersects)
            if intersects is not None
            else None
        )
        datetime_filter = (
            self._parse_datetime_interval(datetime) if datetime is not None else None
        )

        items = chain.from_iterable(
            collection.get_items()
            for collection in self._get_matching_collections(
                collections=collections,
                extra_fields=extra_fields,
                bbox=bbox_filter,
                intersects_bbox=intersects_filter,
                datetime_interval=datetime_filter,
            )
        )
        items = (
            item
            for item in items
            if self._matches_item_filters(
                item,
                ids=ids_filter,
                bbox=bbox_filter,
                intersects_bbox=intersects_filter,
                datetime_interval=datetime_filter,
            )
        )
        if limit is None:
            return items
        return islice(items, limit)

    def list_collections(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        intersects: object | None = None,
        datetime: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """List catalog collections with optional filtering."""
        bbox_filter = self._get_xy_bbox(bbox) if bbox is not None else None
        intersects_filter = (
            self._xy_bbox_from_geojson_geometry(intersects)
            if intersects is not None
            else None
        )
        datetime_filter = (
            self._parse_datetime_interval(datetime) if datetime is not None else None
        )

        return [
            {
                "id": collection.id,
                "title": collection.title,
                "description": collection.description,
                "bbox": self._collection_bbox(collection),
                "start_datetime": self._collection_start_datetime(collection),
                "end_datetime": self._collection_end_datetime(collection),
                "extra_fields": collection.extra_fields,
            }
            for collection in self._get_matching_collections(
                collections=collections,
                extra_fields=extra_fields,
                bbox=bbox_filter,
                intersects_bbox=intersects_filter,
                datetime_interval=datetime_filter,
            )
        ]

    def load(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        intersects: object | None = None,
        datetime: str | None = None,
        ids: list[str] | None = None,
        limit: int | None = None,
        extra_fields: dict[str, Any] | None = None,
        crs: str = "EPSG:2193",
        resolution: float = 100,
        **kwargs: object,
    ) -> xr.Dataset:
        """Mimic `odc.stac.load` on a STAC catalog."""
        items = list(
            self.search(
                collections=collections,
                extra_fields=extra_fields,
                ids=ids,
                bbox=bbox,
                intersects=intersects,
                datetime=datetime,
                limit=limit,
            )
        )
        if not items:
            msg = "No items match the provided search filters"
            raise ValueError(msg)
        ds = odc.stac.load(
            items,
            crs=crs,
            resolution=resolution,
            **kwargs,
        )
        return ds

    def _get_matching_collections(
        self,
        *,
        collections: list[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        intersects_bbox: tuple[float, float, float, float] | None = None,
        datetime_interval: tuple[datetime | None, datetime | None] | None = None,
    ) -> Iterator[Collection]:
        collection_ids = set(collections) if collections is not None else None
        for collection in self.client.get_collections():
            if collection_ids is not None and collection.id not in collection_ids:
                continue
            if not self._matches_extra_fields(collection, extra_fields):
                continue
            if bbox is not None and not self._collection_intersects_bbox(collection, bbox):
                continue
            if intersects_bbox is not None and not self._collection_intersects_bbox(
                collection, intersects_bbox
            ):
                continue
            if datetime_interval is not None and not self._collection_matches_datetime(
                collection, datetime_interval
            ):
                continue
            yield collection

    @staticmethod
    def _matches_extra_fields(
        collection: Collection,
        extra_fields: dict[str, Any] | None,
    ) -> bool:
        if extra_fields is None:
            return True
        return all(
            key in collection.extra_fields and collection.extra_fields[key] == value
            for key, value in extra_fields.items()
        )

    @staticmethod
    def _raise_if_unsupported(**kwargs: object) -> None:
        for name, value in kwargs.items():
            if value is not None:
                msg = f"{name} is not supported for local catalog search"
                raise NotImplementedError(msg)

    def _matches_item_filters(
        self,
        item: Item,
        *,
        ids: set[str] | None,
        bbox: tuple[float, float, float, float] | None,
        intersects_bbox: tuple[float, float, float, float] | None,
        datetime_interval: tuple[datetime | None, datetime | None] | None,
    ) -> bool:
        if ids is not None and item.id not in ids:
            return False
        if bbox is not None and not self._bbox_intersects(item, bbox):
            return False
        if intersects_bbox is not None and not self._item_intersects(item, intersects_bbox):
            return False
        if datetime_interval is not None and not self._matches_datetime(
            item, datetime_interval
        ):
            return False
        return True

    @staticmethod
    def _bbox_intersects(
        item: Item,
        query_bbox: tuple[float, float, float, float],
    ) -> bool:
        item_bbox = item.bbox
        if item_bbox is None:
            return False

        try:
            item_minx, item_miny, item_maxx, item_maxy = StacCatalogClient._get_xy_bbox(
                item_bbox
            )
        except ValueError:
            return False

        return StacCatalogClient._bbox_values_intersect(
            (item_minx, item_miny, item_maxx, item_maxy), query_bbox
        )

    @classmethod
    def _item_intersects(
        cls,
        item: Item,
        query_bbox: tuple[float, float, float, float],
    ) -> bool:
        item_bbox = cls._xy_bbox_from_geojson_geometry(item.geometry)
        if item_bbox is None and item.bbox is not None:
            try:
                item_bbox = cls._get_xy_bbox(item.bbox)
            except ValueError:
                return False
        if item_bbox is None:
            return False
        return cls._bbox_values_intersect(item_bbox, query_bbox)

    @staticmethod
    def _bbox_values_intersect(
        a: tuple[float, float, float, float],
        b: tuple[float, float, float, float],
    ) -> bool:
        a_minx, a_miny, a_maxx, a_maxy = a
        b_minx, b_miny, b_maxx, b_maxy = b

        return not (
            a_maxx < b_minx
            or a_minx > b_maxx
            or a_maxy < b_miny
            or a_miny > b_maxy
        )

    @classmethod
    def _matches_datetime(
        cls,
        item: Item,
        datetime_interval: tuple[datetime | None, datetime | None],
    ) -> bool:
        item_datetime = item.datetime
        if item_datetime is not None:
            point = cls._normalise_utc_datetime(item_datetime)
            return cls._intervals_overlap((point, point), datetime_interval)

        item_start = cls._property_to_datetime(item.properties.get("start_datetime"))
        item_end = cls._property_to_datetime(item.properties.get("end_datetime"))
        if item_start is None and item_end is None:
            return False
        return cls._intervals_overlap((item_start, item_end), datetime_interval)

    @classmethod
    def _collection_matches_datetime(
        cls,
        collection: Collection,
        datetime_interval: tuple[datetime | None, datetime | None],
    ) -> bool:
        temporal = collection.extent.temporal
        for interval in temporal.intervals:
            if interval is None or len(interval) != 2:
                continue
            start = cls._property_to_datetime(interval[0])
            end = cls._property_to_datetime(interval[1])
            if cls._intervals_overlap((start, end), datetime_interval):
                return True
        return False

    @classmethod
    def _collection_intersects_bbox(
        cls,
        collection: Collection,
        query_bbox: tuple[float, float, float, float],
    ) -> bool:
        spatial = collection.extent.spatial
        for bbox in spatial.bboxes:
            if bbox is None:
                continue
            try:
                collection_bbox = cls._get_xy_bbox(bbox)
            except ValueError:
                continue
            if cls._bbox_values_intersect(collection_bbox, query_bbox):
                return True
        return False

    @classmethod
    def _collection_bbox(cls, collection: Collection) -> list[float] | None:
        spatial = collection.extent.spatial
        for bbox in spatial.bboxes:
            if bbox is None:
                continue
            try:
                west, south, east, north = cls._get_xy_bbox(bbox)
            except ValueError:
                continue
            return [west, south, east, north]
        return None

    @classmethod
    def _collection_start_datetime(cls, collection: Collection) -> str | None:
        start, _ = cls._collection_datetime_bounds(collection)
        return start

    @classmethod
    def _collection_end_datetime(cls, collection: Collection) -> str | None:
        _, end = cls._collection_datetime_bounds(collection)
        return end

    @classmethod
    def _collection_datetime_bounds(
        cls,
        collection: Collection,
    ) -> tuple[str | None, str | None]:
        temporal = collection.extent.temporal
        for interval in temporal.intervals:
            if interval is None or len(interval) != 2:
                continue
            start = cls._property_to_datetime(interval[0])
            end = cls._property_to_datetime(interval[1])
            start_value = start.isoformat() if start is not None else None
            end_value = end.isoformat() if end is not None else None
            return start_value, end_value
        return None, None

    @classmethod
    def _property_to_datetime(cls, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return cls._normalise_utc_datetime(value)
        if isinstance(value, str):
            return cls._parse_datetime_value(value)
        return None

    @staticmethod
    def _intervals_overlap(
        left: tuple[datetime | None, datetime | None],
        right: tuple[datetime | None, datetime | None],
    ) -> bool:
        left_start, left_end = left
        right_start, right_end = right

        if left_end is not None and right_start is not None and left_end < right_start:
            return False
        if left_start is not None and right_end is not None and left_start > right_end:
            return False
        return True

    @classmethod
    def _parse_datetime_interval(
        cls,
        datetime_filter: str,
    ) -> tuple[datetime | None, datetime | None]:
        if "/" not in datetime_filter:
            point = cls._parse_datetime_value(datetime_filter)
            return point, point

        start_str, end_str = datetime_filter.split("/", maxsplit=1)
        start = None if start_str in {"", ".."} else cls._parse_datetime_value(start_str)
        end = None if end_str in {"", ".."} else cls._parse_datetime_value(end_str)
        return start, end

    @staticmethod
    def _parse_datetime_value(value: str) -> datetime:
        normalised = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalised)
        return StacCatalogClient._normalise_utc_datetime(parsed)

    @staticmethod
    def _normalise_utc_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @classmethod
    def _xy_bbox_from_geojson_geometry(
        cls,
        geometry: object,
    ) -> tuple[float, float, float, float] | None:
        if geometry is None:
            return None
        if not isinstance(geometry, dict):
            msg = "intersects must be a GeoJSON geometry object"
            raise ValueError(msg)
        coordinates = geometry.get("coordinates")
        if coordinates is None:
            msg = "intersects geometry must include coordinates"
            raise ValueError(msg)

        xmin, ymin, xmax, ymax = cls._xy_bounds_from_coordinates(coordinates)
        return xmin, ymin, xmax, ymax

    @classmethod
    def _xy_bounds_from_coordinates(
        cls,
        coordinates: object,
    ) -> tuple[float, float, float, float]:
        if isinstance(coordinates, (list, tuple)):
            if len(coordinates) >= 2 and all(
                isinstance(value, (int, float)) for value in coordinates[:2]
            ):
                x = float(coordinates[0])
                y = float(coordinates[1])
                return x, y, x, y

            boxes = [cls._xy_bounds_from_coordinates(value) for value in coordinates]
            if not boxes:
                msg = "intersects geometry coordinates are empty"
                raise ValueError(msg)
            minx = min(b[0] for b in boxes)
            miny = min(b[1] for b in boxes)
            maxx = max(b[2] for b in boxes)
            maxy = max(b[3] for b in boxes)
            return minx, miny, maxx, maxy

        msg = "intersects geometry coordinates are invalid"
        raise ValueError(msg)

    @staticmethod
    def _get_xy_bbox(bbox: list[float]) -> tuple[float, float, float, float]:
        if len(bbox) == 4:
            west, south, east, north = bbox
            return west, south, east, north
        if len(bbox) == 6:
            west, south, _minz, east, north, _maxz = bbox
            return west, south, east, north
        msg = "bbox must have 4 (2D) or 6 (3D) coordinates"
        raise ValueError(msg)
