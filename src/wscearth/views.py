"""WSC Earth is a flask app which renders a map of the current car positions."""

import os

import flask
import flask_cachecontrol
import flask_googlemaps
from influxdb_client_3 import InfluxDBClient3

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app,cache # pylint: disable=cyclic-import

INFLUX_URL = os.environ.get(
    "INFLUX_URL", "https://us-east-1-1.aws.cloud2.influxdata.com"
)
INFLUX_ORG = os.environ.get("INFLUX_ORG", "Bridgestone World Solar Challenge")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", None)

INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "test")

QUERY_TIME = os.environ.get("QUERY_TIME", "-2d")


if not INFLUX_TOKEN:
    raise ValueError("No InfluxDB token set using INFLUX_TOKEN "
                     "environment variable")

client = InfluxDBClient3(host=INFLUX_URL,
                         token=INFLUX_TOKEN,
                         org=INFLUX_ORG,
                         database=INFLUX_BUCKET)




# SEt up Google Maps
# Get the Gogole Maps API key
app.config["GOOGLEMAPS_KEY"] = os.environ.get("GOOGLEMAPS_KEY", None)
print(f"Got GoogleMaps Key: {os.environ.get('GOOGLEMAPS_KEY', None)}")

flask_googlemaps.GoogleMaps(app)

# See https://github.com/flask-extensions/Flask-GoogleMaps
# for details of the flask googlemaps extension.


@app.route("/")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def positions():
    """Render a positions map"""
#    query = "select * from telemetry GROUP BY car"
    query = """\
SELECT LAST(latitude),latitude,longitude,*
FROM "telemetry"
WHERE
time >= now() - 1d
GROUP BY shortname"""

    table = client.query(query=query, database=INFLUX_BUCKET, language="influxql")

    # Convert to dataframe
    df = table.to_pandas().sort_values(by="time")
    print(df)
    #print(df.to_markdown())

    # lats = []
    # longs = []

    # for row in rows:
    #     lats.append(row["latitude"])
    #     longs.append(row["longitude"])

    #for _,row in df.iterrows():
    #    print(row)

    if len(df) == 0:
        return flask.render_template("positions_map.html",
                                    centre_lat=-25.0,
                                    centre_long=130.0,
                                    df=[])

    return flask.render_template("positions_map.html",
                                    centre_lat=df["latitude"].mean(),
                                    centre_long=df["longitude"].mean(),
                                    df=df)
