# ruff: noqa: D103

import tomllib
from pathlib import Path


def project_metadata():
    return tomllib.loads(Path("pyproject.toml").read_text())


def test_default_dependencies_are_stac_only():
    dependencies = set(project_metadata()["project"]["dependencies"])

    assert "pystac>=1.14.3" in dependencies
    assert "pystac-client>=0.9.0" in dependencies
    assert "requests-cache>=1.3.1" in dependencies
    assert "shapely>=2.1.2" in dependencies
    assert not any(dependency.startswith("gdal") for dependency in dependencies)
    assert not any(dependency.startswith("cloudpathlib") for dependency in dependencies)


def test_gdal_extra_installs_raster_build_dependencies():
    optional_dependencies = project_metadata()["project"]["optional-dependencies"]

    assert set(optional_dependencies["gdal"]) == {
        "cloudpathlib[s3]>=0.23.0",
        "gdal>=3.11.4",
    }
