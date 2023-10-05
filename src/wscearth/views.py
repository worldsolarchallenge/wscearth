import os
import statistics

import flask
#import flask_googlemaps
from influxdb_client import InfluxDBClient

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app

INFLUX_URL = os.environ.get(
    "INFLUX_URL", "https://eastus-1.azure.cloud2.influxdata.com"
)
INFLUX_ORG = os.environ.get("INFLUX_ORG", "BWSC")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", None)

INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "sample")

QUERY_TIME = os.environ.get("QUERY_TIME", "-2d")


if not INFLUX_TOKEN:
    raise ValueError("No InfluxDB token set using INFLUX_TOKEN "
                     "environment variable")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG,
                        debug=True)


# SEt up Google Maps
# Get the Gogole Maps API key
app.config["GOOGLEMAPS_KEY"] = os.environ.get("GOOGLEMAPS_KEY", None)
print(f"Got GoogleMaps Key: {os.environ.get('GOOGLEMAPS_KEY', None)}")

#flask_googlemaps.GoogleMaps(app)

# See https://github.com/flask-extensions/Flask-GoogleMaps
# for details of the flask googlemaps extension.


@app.route("/")
def positions():
    query_api = client.query_api()

    query = f"""
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: {QUERY_TIME})
            |> filter(fn: (r) => r._measurement == "telemetry"
                                 and (r._field == "latitude"
                                 or r._field == "longitude"
                                 or r._field == "distance"
                                 or r._field == "solarEnergy"
                                 or r._field == "batteryEnergy"))
            |> last()
            |> keep(columns: ["shortname", "_field", "_value"])
            |> pivot(rowKey: ["shortname"],
                              columnKey: ["_field"],
                              valueColumn: "_value")
            |> map(fn: (r) => ({{r with consumption:
                              (r.solarEnergy +
                                r.batteryEnergy)/r.distance}}))
            |> group()
            |> keep(columns: ["shortname", "distance",
                    "latitude", "longitude", "consumption"])"""

    stream = query_api.query_stream(query)
    rows = list(stream)

    lats = []
    longs = []

    for row in rows:
        lats.append(row["latitude"])
        longs.append(row["longitude"])

    if len(rows) != 0:
        return flask.render_template("positions_map.html",
                                     centre_lat=statistics.mean(lats),
                                     centre_long=statistics.mean(longs),
                                     rows=rows)
    else:
        return flask.render_template("positions_map.html",
                                     centre_lat=-25.0,
                                     centre_long=130.0,
                                     rows=[])


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
