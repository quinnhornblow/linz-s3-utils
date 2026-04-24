from pystac import Item

from linz_s3_utils.stac import StacCatalogClient, _filter_collections


class TestStacCatalogClient:
    client = StacCatalogClient(
        "https://nz-elevation.s3-ap-southeast-2.amazonaws.com/catalog.json"
    )

    def test_search_instance(self):
        search = self.client.search()
        assert isinstance(next(search), Item)

    def test_filter_geospatial_category(self):
        all_collections = self.client.client.get_collections()
        filtered_collections = _filter_collections(
            all_collections, linz_geospatial_category="dem"
        )
        assert "01HQS6C8F88JGM04345RY84N9D" in [c.id for c in filtered_collections]
        assert "01HQS6CAGWRKSSF27B93CNZ33E" not in [c.id for c in filtered_collections]
