# ruff: noqa: D103
from collections.abc import Iterator

import xarray as xr

from linz_s3_utils.stac import StacCatalogClient


def test_stac_catalog_client_instance():
    client = StacCatalogClient()
    assert isinstance(client.search(), Iterator)
    assert isinstance(client.load(), xr.Dataset)
