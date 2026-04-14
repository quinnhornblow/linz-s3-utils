FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.5

# Install UV and build-essential
COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential

# Copy the project into the image
WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md ./
COPY src ./src

# Set environment variables for UV
ENV UV_NO_DEV=1
ENV UV_LOCKED=1

RUN uv sync

CMD ["uv", "run", "build-nz-dem", "--", "--help"]
