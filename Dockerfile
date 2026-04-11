FROM ghcr.io/osgeo/gdal:ubuntu-full-latest

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml .
COPY uv.lock .


RUN /root/.local/bin/uv pip compile pyproject.toml -o requirements.txt
RUN /root/.local/bin/uv pip install --system --break-system-packages --no-cache -r requirements.txt
