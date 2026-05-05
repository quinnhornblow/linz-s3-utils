import xarray as xr

from linz_s3_utils.stac import StacCatalogClient


class ElevationClient(StacCatalogClient):
    """Client for accessing elevation data from a STAC catalog."""

    def __init__(self):
        super().__init__(catalog="elevation")

    def load_latest_lidar(self) -> xr.Dataset:
        """Load LiDAR DEM data from the STAC catalog."""
        collection_id = (
            "01JE4ZZWAG19KPKRHYJJP02HC9"  # Collection ID for New Zealand LiDAR 1m DEM
        )
        return self.load(
            collection_ids=[collection_id],
        )
