from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import List

import requests_cache
from pystac import Collection, Item
from pystac_client import Client
from pystac_client.item_search import (
    BBoxLike,
    DatetimeLike,
    IntersectsLike,
)
from pystac_client.stac_api_io import StacApiIO
from shapely.geometry import box, shape

stac_io = StacApiIO()
cache_file = Path(__file__).parent / "stac_cache.sqlite"
stac_io.session = requests_cache.CachedSession(
    cache_name=str(cache_file),
    expire_after=3600,
)


class StacCatalogClient:
    def __init__(self, catalog_url: str):
        self.client = Client.open(
            catalog_url,
            stac_io=stac_io,
        )

    def search(
        self,
        # *,
        bbox: BBoxLike | None = None,
        intersects: IntersectsLike | None = None,
        datetime: DatetimeLike | None = None,
        gsd: int | None = None,
        linz_filters: dict | None = None,
        sortby: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Item]:

        collections = self.client.get_collections()

        filtered_collections = _filter_collections(
            collections, bbox, intersects, datetime, gsd, **(linz_filters or {})
        )

        for collection in filtered_collections:
            collection_items = collection.get_items()
            yield from _filter_items(collection_items, bbox, intersects, datetime)


def _filter_collections(
    collections: Iterable[Collection],
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
    gsd: int | None = None,
    **kwargs,
) -> List[Collection]:
    filtered_collections = []
    for collection in collections:
        if gsd:
            collection_gsd = collection.extra_fields.get("gsd")
            if collection_gsd != gsd:
                continue
        if datetime:
            if not collection.extent.temporal:
                continue
            collection_start = collection.extent.temporal.interval[0][0]
            collection_end = collection.extent.temporal.interval[0][1]
        if bbox and not box(*collection.extent.spatial.bboxes[0]).intersects(bbox):
            continue
        for key, value in kwargs.items():
            if key.startswith("linz_"):
                key = key.replace("linz_", "linz:")
            if collection.extra_fields.get(key) != value:
                break
        filtered_collections.append(collection)
    return filtered_collections


def _filter_items(
    items: Iterable[Item],
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
) -> Iterator[Item]:
    for item in items:
        if bbox and not shape(item.geometry).intersects(bbox):
            continue
        if intersects and not item.geometry.intersects(
            pystac.geometry.shape(intersects)
        ):
            continue
        if datetime and not item.datetime:
            continue
        if datetime and not item.datetime.replace(tzinfo=None) in datetime:
            continue
        yield item
