FROM python:3.11.6-slim

ENV GOOGLEMAPS_KEY
ENV INFLUX_TOKEN

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir /app

ENTRYPOINT ["python"]
CMD ["/usr/local/bin/flask", "--app", "wscearth", "run"]