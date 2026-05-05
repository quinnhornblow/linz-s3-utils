# ruff: noqa: D103

from datetime import datetime, timezone

from pystac import Collection, Extent, Item, SpatialExtent, TemporalExtent
from shapely.geometry import box, mapping

from linz_s3_utils.stac import _io


def collection(
    collection_id: str,
    bbox=(0, 0, 10, 10),
    interval=None,
    **extra_fields,
) -> Collection:
    return Collection(
        id=collection_id,
        description=collection_id,
        extent=Extent(
            SpatialExtent([bbox]),
            TemporalExtent([interval or [None, None]]),
        ),
        extra_fields=extra_fields,
    )


def item(item_id: str, geometry, dt: datetime) -> Item:
    return Item(
        id=item_id,
        geometry=mapping(geometry),
        bbox=list(geometry.bounds),
        datetime=dt,
        properties={},
    )


def test_filter_collections_matches_linz_filters_and_gsd():
    collections = [
        collection(
            "dem-auckland",
            gsd=1,
            **{"linz:geospatial_category": "dem", "linz:region": "auckland"},
        ),
        collection(
            "dsm-auckland",
            gsd=1,
            **{"linz:geospatial_category": "dsm", "linz:region": "auckland"},
        ),
        collection(
            "dem-wellington",
            gsd=8,
            **{"linz:geospatial_category": "dem", "linz:region": "wellington"},
        ),
    ]

    filtered = _io._filter_collections(
        collections,
        gsd=1,
        linz_geospatial_category="dem",
        linz_region="auckland",
    )

    assert [c.id for c in filtered] == ["dem-auckland"]


def test_filter_items_matches_bbox_and_datetime():
    items = [
        item("match", box(0, 0, 10, 10), datetime(2021, 9, 2, tzinfo=timezone.utc)),
        item(
            "outside-space",
            box(20, 20, 30, 30),
            datetime(2021, 9, 2, tzinfo=timezone.utc),
        ),
        item(
            "outside-time",
            box(0, 0, 10, 10),
            datetime(2021, 10, 2, tzinfo=timezone.utc),
        ),
    ]

    filtered = _io._filter_items(
        items,
        bbox=(5, 5, 6, 6),
        datetime="2021-09-01/2021-09-03",
    )

    assert [i.id for i in filtered] == ["match"]


def test_search_sorts_and_limits_results():
    class FakeCollection:
        def __init__(self, items):
            self.id = "collection"
            self.extra_fields = {"gsd": 1}
            self.extent = Extent(
                SpatialExtent([[0, 0, 10, 10]]),
                TemporalExtent([[None, None]]),
            )
            self._items = items

        def get_items(self):
            return self._items

    class FakeClient:
        def __init__(self, collections):
            self._collections = collections

        def get_collections(self):
            return self._collections

    items = [
        item("late", box(0, 0, 1, 1), datetime(2021, 9, 3, tzinfo=timezone.utc)),
        item("early", box(0, 0, 1, 1), datetime(2021, 9, 1, tzinfo=timezone.utc)),
    ]

    search_client = _io.StacCatalogClient.__new__(_io.StacCatalogClient)
    search_client.client = FakeClient([FakeCollection(items)])

    results = list(search_client.search(sortby="datetime", max_items=1))

    assert [result.id for result in results] == ["early"]


def test_make_datetime_range_expands_month_values():
    start, end = _io.make_datetime_range("2021-09")

    assert start == datetime(2021, 9, 1)
    assert end == datetime(2021, 9, 30, 23, 59, 59, 999999)
