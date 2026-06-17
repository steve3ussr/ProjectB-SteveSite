FROM python:3.12-slim AS builder
WORKDIR /build
RUN --mount=type=cache,target=/root/.cache/pip pip install "build>=1.5.0" "setuptools>=82.0.1" "wheel>=0.47.0"
COPY . ./
RUN python3 -m build --no-isolation


FROM python:3.12-slim
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install waitress -r requirements.txt
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
CMD ["waitress-serve", "--host=0.0.0.0", "--threads=16", "--port=5090", "--call", "steve_site:create_app"]
