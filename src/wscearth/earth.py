"""WSC Earth is a flask app which renders a map of the current car positions."""

import os

import flask
import flask_cachecontrol
from influxdb_client_3 import InfluxDBClient3
import simplejson as json

import wscearth.influx

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app,cache # pylint: disable=cyclic-import

# Create an InfluxDB client object. It may make sense to have the app own this.
client = InfluxDBClient3(host=app.config["INFLUX_URL"],
                         token=app.config["INFLUX_TOKEN"],
                         org=app.config["INFLUX_ORG"],
                         database=app.config["INFLUX_BUCKET"])

wsc_influx = wscearth.influx.WSCInflux(client)

@app.route("/earth/earth.kml")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def kml():
    """Render a KML of the event"""

    return wsc_influx.get_positions().to_json(orient="records")

    return "FIXME: Render a KML here"

@app.route("/earth/earth.kmz")
@cache.cached()
def kmz(shortname):
    """Render a KMZ"""

    return "FIXME: Render a KMZ here"
