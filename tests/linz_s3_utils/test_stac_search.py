from datetime import datetime, timezone

import pystac
from pystac_client.item_search import ItemSearch

from linz_s3_utils.stac import search


def build_catalog() -> pystac.Catalog:
    catalog = pystac.Catalog(id="root", description="Synthetic search fixture")

    north = pystac.Collection(
        id="north-dem",
        description="North DEM",
        extent=pystac.Extent(
            pystac.SpatialExtent([[174.70, -36.95, 174.95, -36.75]]),
            pystac.TemporalExtent(
                [[datetime(2024, 1, 1, tzinfo=timezone.utc), None]]
            ),
        ),
        extra_fields={
            "linz:region": "auckland",
            "linz:slug": "auckland-north_2016-2018",
            "linz:geospatial_category": "dem",
        },
    )

    item = pystac.Item(
        id="tile-001",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [174.80, -36.90],
                    [174.90, -36.90],
                    [174.90, -36.80],
                    [174.80, -36.80],
                    [174.80, -36.90],
                ]
            ],
        },
        bbox=[174.80, -36.90, 174.90, -36.80],
        datetime=datetime(2024, 3, 14, tzinfo=timezone.utc),
        properties={"created": "2024-03-14T00:00:00Z", "gsd": 1.0},
    )
    north.add_item(item)
    catalog.add_child(north)
    return catalog


def test_search_returns_real_item_search() -> None:
    catalog = build_catalog()

    item_search = search(catalog, ids=["tile-001"])

    assert isinstance(item_search, ItemSearch)
    assert [item.id for item in item_search.items()] == ["tile-001"]
