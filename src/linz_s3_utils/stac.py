from collections.abc import Iterator
from enum import Enum
from pathlib import Path
from typing import Literal
from warnings import filterwarnings

import odc.stac
import requests_cache
import xarray as xr
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
        self.client = Client.open(CatalogURLs[catalog.upper()].value, stac_io=stac_io)

    def search(
        self,
    ) -> Iterator[Item]:
        """Mimic `pystac_client.Client.search` on a STAC catalog."""
        return next(self.client.get_collections()).get_items()

    def list_collections(self) -> list[dict[str, str | None]]:
        """List ids and titles of collections in the catalog."""
        return [
            {"id": collection.id, "title": collection.title}
            for collection in self.client.get_collections()
        ]

    def load(
        self,
    ) -> xr.Dataset:
        """Mimic `odc.stac.load` on a STAC catalog."""
        items = self.search()
        ds = odc.stac.load(
            items,
            crs="EPSG:2193",
            resolution=100,
        )
        return ds
