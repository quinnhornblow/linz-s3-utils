from linz_s3_utils.cli import build_nz_dem


def test_build_nz_dem(capsys):
    test_args = [
        "build_nz_dem",
        "-r",
        "10",
        "--output-directory",
        "tests/linz_s3_utils/test_data",
        "--overwrite",
    ]
    build_nz_dem(test_args)
