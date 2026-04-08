import subprocess


def build_vrt(s3_dir, output_vrt, extension=".tiff"):
    """Build a VRT file from all files in the given S3 directory."""
    tif_files = sorted(s3_dir.rglob(f"*{extension}"), key=str)
    if not tif_files:
        print(f"No {extension} files found in {s3_dir}")
        return

    # Build the VRT command
    input_files_str = " ".join(str(tif) for tif in tif_files)
    vrt_command = f"gdalbuildvrt {output_vrt} {input_files_str}"
    print(f"Running command: {vrt_command}")

    # Execute the command
    subprocess.run(vrt_command, shell=True, check=True)
