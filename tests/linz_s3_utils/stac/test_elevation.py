# # ruff: noqa: D101,D102,D103

# from datetime import datetime, timezone
# from inspect import Parameter, signature

# from pystac import Collection, Extent, Item, SpatialExtent, TemporalExtent
# from shapely.geometry import box, mapping

# from linz_s3_utils.stac import StacCatalogClient, _filter_collections, _filter_items


# def collection(
#     collection_id,
#     bbox=(0, 0, 10, 10),
#     interval=None,
#     **extra_fields,
# ):
#     return Collection(
#         id=collection_id,
#         description=collection_id,
#         extent=Extent(
#             SpatialExtent([bbox]),
#             TemporalExtent([interval or [None, None]]),
#         ),
#         extra_fields=extra_fields,
#     )


# def item(item_id, geom, dt):
#     return Item(
#         id=item_id,
#         geometry=mapping(geom),
#         bbox=list(geom.bounds),
#         datetime=dt,
#         properties={},
#     )


# class TestStacCatalogClient:
#     client = StacCatalogClient(
#         "https://nz-elevation.s3-ap-southeast-2.amazonaws.com/catalog.json"
#     )

#     def test_search_instance(self):
#         search = self.client.search()
#         assert isinstance(next(search), Item)

#     def test_filter_geospatial_category(self):
#         all_collections = self.client.client.get_collections()
#         filtered_collections = _filter_collections(
#             all_collections, linz_geospatial_category="dem"
#         )
#         assert "01HQS6C8F88JGM04345RY84N9D" in [c.id for c in filtered_collections]
#         assert "01HQS6CAGWRKSSF27B93CNZ33E" not in [c.id for c in filtered_collections]

#     def test_search(self):
#         search = self.client.search(
#             bbox=box(168.06, -46.90, 168.11, -46.84),
#             datetime="2021-09-01/2021-09-03",
#             gsd=1,
#             linz_filters={
#                 "linz_geospatial_category": "dem",
#                 "linz_region": "southland",
#             },
#         )
#         items = list(search)
#         assert len(items) == 1


# def test_filter_collections_matches_all_linz_filters():
#     collections = [
#         collection(
#             "dem-auckland",
#             **{"linz:geospatial_category": "dem", "linz:region": "auckland"},
#         ),
#         collection(
#             "dsm-auckland",
#             **{"linz:geospatial_category": "dsm", "linz:region": "auckland"},
#         ),
#         collection(
#             "dem-wellington",
#             **{"linz:geospatial_category": "dem", "linz:region": "wellington"},
#         ),
#     ]

#     filtered = _filter_collections(
#         collections,
#         linz_geospatial_category="dem",
#         linz_region="auckland",
#     )

#     assert [c.id for c in filtered] == ["dem-auckland"]


# def test_filter_collections_matches_bbox_tuple_and_gsd():
#     collections = [
#         collection("inside", bbox=(0, 0, 10, 10), gsd=1),
#         collection("wrong-gsd", bbox=(0, 0, 10, 10), gsd=8),
#         collection("outside", bbox=(20, 20, 30, 30), gsd=1),
#     ]

#     filtered = _filter_collections(collections, bbox=(5, 5, 6, 6), gsd=1)

#     assert [c.id for c in filtered] == ["inside"]


# def test_search_arguments_match_pystac_client_keyword_only_style():
#     parameters = signature(StacCatalogClient.search).parameters

#     assert parameters["bbox"].kind is Parameter.KEYWORD_ONLY


# def test_filter_collections_matches_requested_collection_ids():
#     collections = [
#         collection("dem-auckland"),
#         collection("dem-wellington"),
#     ]

#     filtered = _filter_collections(collections, collections="dem-wellington")

#     assert [c.id for c in filtered] == ["dem-wellington"]


# def test_filter_collections_matches_overlapping_datetime_interval():
#     collections = [
#         collection(
#             "before",
#             interval=[
#                 datetime(2020, 1, 1, tzinfo=timezone.utc),
#                 datetime(2020, 12, 31, tzinfo=timezone.utc),
#             ],
#         ),
#         collection(
#             "overlaps",
#             interval=[
#                 datetime(2021, 8, 1, tzinfo=timezone.utc),
#                 datetime(2021, 10, 1, tzinfo=timezone.utc),
#             ],
#         ),
#     ]

#     filtered = _filter_collections(collections, datetime="2021-09-01/2021-09-03")

#     assert [c.id for c in filtered] == ["overlaps"]


# def test_filter_collections_expands_simple_date_strings():
#     collections = [
#         collection(
#             "date-match",
#             interval=[
#                 datetime(2021, 9, 1, 12, tzinfo=timezone.utc),
#                 datetime(2021, 9, 1, 12, tzinfo=timezone.utc),
#             ],
#         ),
#         collection(
#             "month-match",
#             interval=[
#                 datetime(2021, 9, 30, 12, tzinfo=timezone.utc),
#                 datetime(2021, 9, 30, 12, tzinfo=timezone.utc),
#             ],
#         ),
#     ]

#     assert [c.id for c in _filter_collections(collections, datetime="2021-09-01")] == [
#         "date-match"
#     ]
#     assert [c.id for c in _filter_collections(collections, datetime="2021-09")] == [
#         "date-match",
#         "month-match",
#     ]


# def test_filter_items_matches_bbox_intersects_and_datetime():
#     items = [
#         item("match", box(0, 0, 10, 10), datetime(2021, 9, 2, tzinfo=timezone.utc)),
#         item(
#             "outside-space",
#             box(20, 20, 30, 30),
#             datetime(2021, 9, 2, tzinfo=timezone.utc),
#         ),
#         item(
#             "outside-time",
#             box(0, 0, 10, 10),
#             datetime(2021, 10, 2, tzinfo=timezone.utc),
#         ),
#     ]

#     filtered = _filter_items(items, bbox=(5, 5, 6, 6), datetime="2021-09-01/2021-09-03")

#     assert [i.id for i in filtered] == ["match"]


# def test_filter_items_matches_requested_item_ids():
#     items = [
#         item("AA01", box(0, 0, 10, 10), datetime(2021, 9, 1, tzinfo=timezone.utc)),
#         item("AA02", box(0, 0, 10, 10), datetime(2021, 9, 1, tzinfo=timezone.utc)),
#     ]

#     filtered = _filter_items(items, ids=["AA02"])

#     assert [i.id for i in filtered] == ["AA02"]


# def test_filter_items_expands_simple_date_strings():
#     items = [
#         item("date-match", box(0, 0, 10, 10), datetime(2021, 9, 1, 12)),
#         item("month-match", box(0, 0, 10, 10), datetime(2021, 9, 30, 12)),
#         item("outside", box(0, 0, 10, 10), datetime(2021, 10, 1, 0)),
#     ]

#     assert [i.id for i in _filter_items(items, datetime="2021-09-01")] == ["date-match"]
#     assert [i.id for i in _filter_items(items, datetime="2021-09")] == [
#         "date-match",
#         "month-match",
#     ]
