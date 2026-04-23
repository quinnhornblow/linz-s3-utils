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

    south = pystac.Collection(
        id="south-imagery",
        description="South Imagery",
        extent=pystac.Extent(
            pystac.SpatialExtent([[175.20, -37.30, 175.45, -37.05]]),
            pystac.TemporalExtent(
                [[datetime(2023, 1, 1, tzinfo=timezone.utc), None]]
            ),
        ),
        extra_fields={
            "linz:region": "waikato",
            "linz:slug": "waikato-south_2019-2020",
            "linz:geospatial_category": "imagery",
        },
    )

    south.add_item(
        pystac.Item(
            id="tile-002",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [175.25, -37.25],
                        [175.35, -37.25],
                        [175.35, -37.15],
                        [175.25, -37.15],
                        [175.25, -37.25],
                    ]
                ],
            },
            bbox=[175.25, -37.25, 175.35, -37.15],
            datetime=datetime(2023, 6, 10, tzinfo=timezone.utc),
            properties={"created": "2023-06-10T00:00:00Z", "gsd": 2.5},
        )
    )

    catalog.add_child(north)
    catalog.add_child(south)
    return catalog


def test_search_returns_real_item_search() -> None:
    catalog = build_catalog()

    item_search = search(catalog, ids=["tile-001"])

    assert isinstance(item_search, ItemSearch)
    assert [item.id for item in item_search.items()] == ["tile-001"]


def test_search_filters_by_ids() -> None:
    catalog = build_catalog()

    matches = search(catalog, ids=["tile-002"])
    misses = search(catalog, ids=["tile-999"])

    assert [item.id for item in matches.items()] == ["tile-002"]
    assert list(misses.items()) == []


def test_search_filters_by_collections() -> None:
    catalog = build_catalog()

    matches = search(catalog, collections=["south-imagery"])
    misses = search(catalog, collections=["missing-collection"])

    assert [item.id for item in matches.items()] == ["tile-002"]
    assert list(misses.items()) == []


def test_search_filters_by_bbox() -> None:
    catalog = build_catalog()

    inside = search(catalog, bbox=[174.75, -36.92, 174.92, -36.79])
    outside = search(catalog, bbox=[175.50, -37.50, 175.60, -37.40])

    assert [item.id for item in inside.items()] == ["tile-001"]
    assert list(outside.items()) == []


def test_search_filters_by_datetime() -> None:
    catalog = build_catalog()

    current = search(catalog, datetime="2024-03-01/2024-03-31")
    old = search(catalog, datetime="2022-01-01/2022-12-31")

    assert [item.id for item in current.items()] == ["tile-001"]
    assert list(old.items()) == []


def test_search_filters_by_query_on_item_properties() -> None:
    catalog = build_catalog()

    matches = search(catalog, query={"gsd": {"lte": 1.0}})
    misses = search(catalog, query={"gsd": {"gt": 2.5}})

    assert [item.id for item in matches.items()] == ["tile-001"]
    assert list(misses.items()) == []


def test_search_filters_by_query_on_top_level_item_field() -> None:
    catalog = build_catalog()

    matches = search(catalog, query={"collection": {"eq": "north-dem"}})
    misses = search(catalog, query={"collection": {"eq": "missing-collection"}})

    assert [item.id for item in matches.items()] == ["tile-001"]
    assert list(misses.items()) == []


def test_search_filters_by_linz_collection_metadata() -> None:
    catalog = build_catalog()

    region = search(catalog, query={"linz:region": {"eq": "auckland"}})
    slug = search(catalog, query={"linz:slug": {"eq": "auckland-north_2016-2018"}})
    category = search(catalog, query={"linz:geospatial_category": {"eq": "dem"}})

    assert [item.id for item in region.items()] == ["tile-001"]
    assert [item.id for item in slug.items()] == ["tile-001"]
    assert [item.id for item in category.items()] == ["tile-001"]


def test_search_pages_respect_limit() -> None:
    catalog = build_catalog()
    collection = catalog.get_child("north-dem")
    assert collection is not None

    for index in range(3, 6):
        collection.add_item(
            pystac.Item(
                id=f"tile-00{index}",
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
        )

    item_search = search(catalog, collections=["north-dem"], limit=2)
    pages = list(item_search.pages_as_dicts())

    assert [len(page["features"]) for page in pages] == [2, 2]


def test_search_matched_counts_before_max_items() -> None:
    catalog = build_catalog()
    collection = catalog.get_child("north-dem")
    assert collection is not None

    for index in range(3, 6):
        collection.add_item(
            pystac.Item(
                id=f"tile-00{index}",
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
        )

    item_search = search(catalog, collections=["north-dem"], limit=2, max_items=1)

    assert item_search.matched() == 4
    assert [item.id for item in item_search.items()] == ["tile-001"]
