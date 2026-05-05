# ruff: noqa: D103
from collections.abc import Iterator

import pytest
import xarray as xr

from linz_s3_utils.stac import StacCatalogClient


def test_stac_catalog_client_instance():
    client = StacCatalogClient()
    assert isinstance(client.search(), Iterator)
    assert isinstance(client.load(), xr.Dataset)


def test_stac_invalid_catalog():
    with pytest.raises(KeyError):
        StacCatalogClient(catalog="invalid")
