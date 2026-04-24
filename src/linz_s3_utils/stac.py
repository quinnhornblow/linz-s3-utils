from collections.abc import Iterable, Iterator
from typing import List

from pystac import Catalog, Collection, Item
from pystac_client.item_search import (
    BBoxLike,
    DatetimeLike,
    IntersectsLike,
)


class StacCatalogClient:
    def __init__(self, catalog_url: str):
        self.catalog = Catalog.from_file(catalog_url)
        self.collections = None

    def search(
        self,
        # *,
        bbox: BBoxLike | None = None,
        intersects: IntersectsLike | None = None,
        datetime: DatetimeLike | None = None,
        linz_filters: dict | None = None,
    ) -> Iterator[Item]:
        if self.collections is None:
            self.collections = _get_collections(self.catalog)

        filtered_collections = _filter_collections(
            self.collections, bbox, intersects, datetime, **(linz_filters or {})
        )

        for collection in filtered_collections:
            collection_items = _get_collection_items(collection)
            yield from _filter_items(collection_items, bbox, intersects, datetime)


def _get_collections(catalog: Catalog) -> List[Collection]:
    return list(catalog.get_collections())


def _filter_collections(
    collections: Iterable[Collection],
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
    **kwargs,
) -> List[Collection]:
    filtered_collections = []
    for collection in collections:
        match = True
        for key, value in kwargs.items():
            if key.startswith("linz_"):
                key = key.replace("linz_", "linz:")
            if collection.extra_fields.get(key) != value:
                match = False
                break
        if match:
            filtered_collections.append(collection)
    return filtered_collections


def _get_collection_items(collection: Collection) -> Iterable[Item]:
    return collection.get_items()


def _filter_items(
    items: Iterable[Item],
    bbox: BBoxLike | None = None,
    intersects: IntersectsLike | None = None,
    datetime: DatetimeLike | None = None,
) -> Iterator[Item]:
    for item in items:
        if bbox and not item.geometry.intersects(pystac.geometry.box(*bbox)):
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
