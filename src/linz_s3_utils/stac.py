from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pystac
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO


class CatalogSearchIO(StacApiIO):
    def __init__(self, catalog: pystac.Catalog) -> None:
        super().__init__()
        self.catalog = catalog

    def get_pages(
        self,
        url: str,
        method: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        raise NotImplementedError

    def read_json(
        self,
        source: str,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError


def search(catalog: pystac.Catalog, **search_kwargs: Any) -> ItemSearch:
    return ItemSearch(
        url="memory://catalog-search",
        stac_io=CatalogSearchIO(catalog),
        client=None,
        **search_kwargs,
    )
