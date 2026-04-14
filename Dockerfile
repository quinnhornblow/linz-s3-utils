FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential

# ENV UV_PYTHON=/usr/bin/python3
# ENV GDAL_CONFIG=/usr/bin/gdal-config

# Copy the project into the image
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

# Presuming there is a `my_app` command provided by the project
CMD ["uv", "run", "build-nz-dem", "--", "--help"]
