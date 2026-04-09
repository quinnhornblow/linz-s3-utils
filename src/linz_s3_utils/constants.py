from cloudpathlib import CloudPath, S3Client

S3_PUBLIC_CLIENT = S3Client(no_sign_request=True)

S3_ELEVATION_DIR = CloudPath("s3://nz-elevation/", client=S3_PUBLIC_CLIENT)

S3_COASTAL_DIR = CloudPath("s3://nz-coastal/", client=S3_PUBLIC_CLIENT)

S3_IMAGERY_DIR = CloudPath("s3://nz-imagery/", client=S3_PUBLIC_CLIENT)
