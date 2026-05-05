# ruff: noqa: D103

from pathlib import Path

from linz_s3_utils import cli


def test_build_nz_dem_parses_and_forwards_arguments(monkeypatch, tmp_path):
    calls = []

    def fake_build_new_zealand_dem(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(cli, "build_new_zealand_dem", fake_build_new_zealand_dem)

    cli.build_nz_dem(
        [
            "--resolution",
            "100",
            "--output-directory",
            str(tmp_path),
            "--overwrite",
            "--export-tiff",
            "--compression",
            "LZW",
        ]
    )

    assert calls == [
        {
            "output_directory": Path(tmp_path),
            "resolution": 100,
            "overwrite": True,
            "export_tiff": True,
            "compression": "LZW",
        }
    ]
