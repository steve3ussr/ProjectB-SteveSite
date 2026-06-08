FROM python:3.12-slim
RUN pip install --no-cache-dir waitress
COPY /dist/steve_site-0.9.0-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/steve_site-0.9.0-py3-none-any.whl \
    && rm /tmp/steve_site-0.9.0-py3-none-any.whl
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5090", "steve_site:create_app"]
