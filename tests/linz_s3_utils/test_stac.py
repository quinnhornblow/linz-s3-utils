# ruff: noqa: D103
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from pystac import Collection, Extent, Item, SpatialExtent, TemporalExtent

from linz_s3_utils.stac import StacCatalogClient


class FakeCatalog:
    """Minimal fake catalog exposing collection iteration."""

    def __init__(self, *collections: Collection):
        """Store fake collections."""
        self._collections = collections

    def get_collections(self) -> Iterator[Collection]:
        """Return an iterator over fake collections."""
        return iter(self._collections)


def make_collection(
    collection_id: str,
    *,
    title: str,
    description: str,
    bbox: list[float] | None = None,
    interval: tuple[datetime | None, datetime | None] = (datetime(2024, 1, 1, tzinfo=UTC), None),
    license: str | None = None,
    keywords: list[str] | None = None,
    extra_fields: dict[str, str] | None = None,
) -> Collection:
    collection_bbox = bbox if bbox is not None else [-180.0, -90.0, 180.0, 90.0]
    start_datetime, end_datetime = interval
    collection = Collection(
        id=collection_id,
        title=title,
        description=description,
        license=license,
        keywords=keywords,
        extent=Extent(
            SpatialExtent([collection_bbox]),
            TemporalExtent([[start_datetime, end_datetime]]),
        ),
    )
    if extra_fields:
        collection.extra_fields.update(extra_fields)
    return collection


def make_item(
    item_id: str,
    *,
    lon: float | None = None,
    lat: float | None = None,
    dt: datetime | None,
    geometry: dict[str, object] | None = None,
    bbox: list[float] | None = None,
    **properties: str,
) -> Item:
    if geometry is None and lon is not None and lat is not None:
        geometry = {"type": "Point", "coordinates": [lon, lat]}
    if bbox is None and lon is not None and lat is not None:
        bbox = [lon, lat, lon, lat]
    return Item(
        id=item_id,
        geometry=geometry,
        bbox=bbox,
        datetime=dt,
        properties=properties,
    )


class FakeStacCatalogClient(StacCatalogClient):
    """Client test double with injectable catalog."""

    def __init__(self, *collections: Collection):
        """Initialise client with an in-memory fake catalog."""
        self.client = FakeCatalog(*collections)


def make_client(*collections: Collection) -> StacCatalogClient:
    return FakeStacCatalogClient(*collections)


def test_search_filters_by_collection_and_extra_fields():
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
        extra_fields={"product": "imagery", "region": "canterbury"},
    )
    aerial.add_item(
        make_item(
            "aerial-item",
            lon=172.63,
            lat=-43.53,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
            platform="sat-a",
        )
    )
    lidar = make_collection(
        "lidar",
        title="LiDAR",
        description="Point cloud tiles",
        extra_fields={"product": "elevation", "region": "canterbury"},
    )
    lidar.add_item(
        make_item(
            "lidar-item",
            lon=172.65,
            lat=-43.55,
            dt=datetime(2024, 1, 17, tzinfo=UTC),
            platform="sat-b",
        )
    )
    hydro = make_collection(
        "hydro",
        title="Hydro",
        description="Hydro layers",
        extra_fields={"product": "imagery", "region": "canterbury"},
    )
    hydro.add_item(
        make_item(
            "hydro-item",
            lon=172.66,
            lat=-43.56,
            dt=datetime(2024, 1, 18, tzinfo=UTC),
            platform="sat-c",
        )
    )
    client = make_client(aerial, lidar, hydro)

    results = list(
        client.search(
            collections=["aerial", "lidar"],
            extra_fields={"product": "imagery", "region": "canterbury"},
        )
    )

    assert [item.id for item in results] == ["aerial-item"]


def test_search_filters_by_ids_bbox_and_datetime():
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
    )
    aerial.add_item(
        make_item(
            "keep-1",
            lon=172.63,
            lat=-43.53,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
            quality="processed",
        )
    )
    aerial.add_item(
        make_item(
            "keep-2",
            lon=172.64,
            lat=-43.54,
            dt=datetime(2024, 1, 20, tzinfo=UTC),
            quality="processed",
        )
    )
    aerial.add_item(
        make_item(
            "outside-bbox",
            lon=174.0,
            lat=-41.0,
            dt=datetime(2024, 1, 18, tzinfo=UTC),
            quality="processed",
        )
    )
    aerial.add_item(
        make_item(
            "outside-datetime",
            lon=172.635,
            lat=-43.535,
            dt=datetime(2023, 12, 31, tzinfo=UTC),
            quality="processed",
        )
    )
    aerial.add_item(
        make_item(
            "not-requested",
            lon=172.636,
            lat=-43.536,
            dt=datetime(2024, 1, 12, tzinfo=UTC),
            quality="processed",
        )
    )
    client = make_client(aerial)

    results = list(
        client.search(
            ids=["keep-1", "keep-2", "outside-bbox", "outside-datetime"],
            bbox=[172.62, -43.56, 172.65, -43.52],
            datetime="2024-01-01T00:00:00Z/2024-01-31T23:59:59Z",
        )
    )

    assert {item.id for item in results} == {"keep-1", "keep-2"}


def test_search_filters_by_intersects_for_item_geometry_and_bbox_fallback():
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
        bbox=[172.0, -44.0, 173.0, -43.0],
    )
    aerial.add_item(
        make_item(
            "inside-geometry",
            dt=datetime(2024, 1, 15, tzinfo=UTC),
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [172.62, -43.56],
                        [172.66, -43.56],
                        [172.66, -43.52],
                        [172.62, -43.52],
                        [172.62, -43.56],
                    ]
                ],
            },
            bbox=[172.62, -43.56, 172.66, -43.52],
        )
    )
    aerial.add_item(
        make_item(
            "outside-geometry",
            dt=datetime(2024, 1, 16, tzinfo=UTC),
            geometry={
                "type": "Point",
                "coordinates": [174.0, -41.0],
            },
            bbox=[174.0, -41.0, 174.0, -41.0],
        )
    )
    aerial.add_item(
        make_item(
            "inside-bbox-fallback",
            dt=datetime(2024, 1, 17, tzinfo=UTC),
            geometry=None,
            bbox=[172.63, -43.55, 172.63, -43.55],
        )
    )
    client = make_client(aerial)

    results = list(
        client.search(
            intersects={
                "type": "Polygon",
                "coordinates": [
                    [
                        [172.61, -43.57],
                        [172.67, -43.57],
                        [172.67, -43.51],
                        [172.61, -43.51],
                        [172.61, -43.57],
                    ]
                ],
            }
        )
    )

    assert {item.id for item in results} == {"inside-geometry", "inside-bbox-fallback"}


def test_search_applies_collection_bbox_and_datetime_filter_path():
    inside = make_collection(
        "inside",
        title="Inside",
        description="Inside extent",
        bbox=[172.0, -44.0, 173.0, -43.0],
        interval=(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 31, tzinfo=UTC)),
    )
    inside.add_item(
        make_item(
            "inside-item",
            lon=172.5,
            lat=-43.5,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
        )
    )
    outside_spatial = make_collection(
        "outside-spatial",
        title="Outside spatial",
        description="Outside extent",
        bbox=[165.0, -47.0, 166.0, -46.0],
        interval=(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 31, tzinfo=UTC)),
    )
    outside_spatial.add_item(
        make_item(
            "outside-spatial-item",
            lon=172.5,
            lat=-43.5,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
        )
    )
    outside_temporal = make_collection(
        "outside-temporal",
        title="Outside temporal",
        description="Outside temporal extent",
        bbox=[172.0, -44.0, 173.0, -43.0],
        interval=(datetime(2023, 1, 1, tzinfo=UTC), datetime(2023, 1, 31, tzinfo=UTC)),
    )
    outside_temporal.add_item(
        make_item(
            "outside-temporal-item",
            lon=172.5,
            lat=-43.5,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
        )
    )
    client = make_client(inside, outside_spatial, outside_temporal)

    results = list(
        client.search(
            bbox=[172.4, -43.6, 172.6, -43.4],
            datetime="2024-01-10T00:00:00Z/2024-01-20T23:59:59Z",
        )
    )

    assert [item.id for item in results] == ["inside-item"]


def test_search_uses_item_start_end_datetime_when_datetime_is_none():
    aerial = make_collection(
        "aerial",
        title="Aerial",
        description="Aerial data",
    )
    aerial.add_item(
        make_item(
            "overlap",
            lon=172.5,
            lat=-43.5,
            dt=None,
            start_datetime="2024-01-10T00:00:00Z",
            end_datetime="2024-01-20T00:00:00Z",
        )
    )
    aerial.add_item(
        make_item(
            "no-overlap",
            lon=172.5,
            lat=-43.5,
            dt=None,
            start_datetime="2024-02-10T00:00:00Z",
            end_datetime="2024-02-20T00:00:00Z",
        )
    )
    client = make_client(aerial)

    results = list(client.search(datetime="2024-01-15T00:00:00Z/2024-01-16T00:00:00Z"))

    assert [item.id for item in results] == ["overlap"]


def test_search_respects_limit_without_assuming_item_order():
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
    )
    aerial.add_item(
        make_item(
            "keep-1",
            lon=172.63,
            lat=-43.53,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
            quality="processed",
        )
    )
    aerial.add_item(
        make_item(
            "keep-2",
            lon=172.64,
            lat=-43.54,
            dt=datetime(2024, 1, 20, tzinfo=UTC),
            quality="processed",
        )
    )
    client = make_client(aerial)

    results = list(client.search(limit=1))

    assert len(results) == 1
    assert results[0].id in {"keep-1", "keep-2"}


def test_list_collections_returns_richer_filtered_summaries():
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
        license="CC-BY-4.0",
        keywords=["imagery", "rgb"],
        extra_fields={"product": "imagery", "region": "canterbury"},
    )
    lidar = make_collection(
        "lidar",
        title="LiDAR",
        description="Point cloud tiles",
        extra_fields={"product": "elevation", "region": "canterbury"},
    )
    hydro = make_collection(
        "hydro",
        title="Hydro",
        description="Hydro layers",
        extra_fields={"product": "imagery", "region": "otago"},
    )
    client = make_client(aerial, lidar, hydro)

    summaries = client.list_collections(
        collections=["aerial", "hydro"],
        bbox=[172.0, -44.0, 173.0, -43.0],
        datetime="2024-01-01T00:00:00Z/2024-02-01T00:00:00Z",
        extra_fields={"product": "imagery", "region": "canterbury"},
    )

    assert summaries == [
        {
            "id": "aerial",
            "title": "Aerial Imagery",
            "description": "High resolution imagery",
            "bbox": [-180.0, -90.0, 180.0, 90.0],
            "start_datetime": "2024-01-01T00:00:00+00:00",
            "end_datetime": None,
            "extra_fields": {"product": "imagery", "region": "canterbury"},
        },
    ]


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("query", {"quality": {"eq": "processed"}}),
        ("filter", "quality = 'processed'"),
        ("sortby", [{"field": "datetime", "direction": "desc"}]),
        ("fields", {"include": ["id", "properties.datetime"]}),
    ],
)
def test_search_rejects_unsupported_parameters(parameter: str, value: object):
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
    )
    client = make_client(aerial)

    with pytest.raises(NotImplementedError, match=parameter):
        list(client.search(**{parameter: value}))


def test_load_forwards_items_and_kwargs(monkeypatch: pytest.MonkeyPatch):
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
        extra_fields={"product": "imagery", "region": "canterbury"},
    )
    aerial.add_item(
        make_item(
            "aerial-item",
            lon=172.63,
            lat=-43.53,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
        )
    )
    lidar = make_collection(
        "lidar",
        title="LiDAR",
        description="Point cloud tiles",
        extra_fields={"product": "elevation", "region": "canterbury"},
    )
    lidar.add_item(
        make_item(
            "lidar-item",
            lon=172.65,
            lat=-43.55,
            dt=datetime(2024, 1, 17, tzinfo=UTC),
        )
    )
    client = make_client(aerial, lidar)

    called: dict[str, object] = {}
    expected = object()

    def fake_load(items: Iterator[Item], **kwargs: object) -> object:
        called["items"] = list(items)
        called["kwargs"] = kwargs
        return expected

    monkeypatch.setattr("linz_s3_utils.stac.odc.stac.load", fake_load)

    result = client.load(
        collections=["aerial"],
        extra_fields={"product": "imagery", "region": "canterbury"},
        chunks={"x": 256, "y": 256},
        resolution=25,
        crs="EPSG:4326",
    )

    assert result is expected
    assert [item.id for item in called["items"]] == ["aerial-item"]
    assert called["kwargs"] == {
        "chunks": {"x": 256, "y": 256},
        "resolution": 25,
        "crs": "EPSG:4326",
    }


def test_load_raises_clear_error_when_no_items_match():
    aerial = make_collection(
        "aerial",
        title="Aerial Imagery",
        description="High resolution imagery",
    )
    aerial.add_item(
        make_item(
            "aerial-item",
            lon=172.63,
            lat=-43.53,
            dt=datetime(2024, 1, 15, tzinfo=UTC),
        )
    )
    client = make_client(aerial)

    with pytest.raises(ValueError, match="No items match"):
        client.load(collections=["missing-collection"])


def test_stac_invalid_catalog():
    with pytest.raises(KeyError):
        StacCatalogClient(catalog="invalid")


def test_integration_real_client_search_limit_returns_iterator():
    client = StacCatalogClient()
    results = client.search(limit=1)

    assert isinstance(results, Iterator)
    assert isinstance(next(results), Item)
    with pytest.raises(StopIteration):
        next(results)
