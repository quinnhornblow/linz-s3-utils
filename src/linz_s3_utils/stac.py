from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pystac
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO


DEFAULT_PAGE_SIZE = 100


class CatalogSearchIO(StacApiIO):
    def __init__(self, catalog: pystac.Catalog) -> None:
        super().__init__()
        self.catalog = catalog

    def _iter_item_dicts(self) -> Iterator[dict[str, Any]]:
        for item in self.catalog.get_items(recursive=True):
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
        matched_items = list(self._iter_item_dicts())
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
        matched_items = list(self._iter_item_dicts())
        page_size = self._page_size(parameters)
        return self._feature_collection(matched_items[:page_size], len(matched_items))


def search(catalog: pystac.Catalog, **search_kwargs: Any) -> ItemSearch:
    return ItemSearch(
        url="memory://catalog-search",
        stac_io=CatalogSearchIO(catalog),
        client=None,
        **search_kwargs,
    )
