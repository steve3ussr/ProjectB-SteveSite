FROM python:3.12-slim AS builder
WORKDIR /build
COPY . ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m build --no-isolation


FROM python:3.12-slim
RUN pip install --no-cache-dir waitress
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5090", "--call", "steve_site:create_app"]
