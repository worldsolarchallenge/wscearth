"""WSC Earth is a flask app which renders a map of the current car positions."""

import os

import flask
import flask_cachecontrol
from influxdb_client_3 import InfluxDBClient3
import simplejson as json

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app,cache # pylint: disable=cyclic-import

client = InfluxDBClient3(host=app.config["INFLUX_URL"],
                         token=app.config["INFLUX_TOKEN"],
                         org=app.config["INFLUX_ORG"],
                         database=app.config["INFLUX_BUCKET"])


@app.route("/")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def index():
    """Render a Google map"""
    return flask.render_template("positions_map.html")

@app.route("/scripts/positions.js")
@cache.cached()
def positions_script():
    """Templated positions.js to allow for base URL rendering"""
    return flask.render_template("positions.js.j2")


@app.route("/api/path/<shortname>")
def api_path(shortname):
    """Render JSON path positions for car"""

    query = f'SELECT * FROM "telemetry" WHERE shortname = \'{shortname}\' and time >= -30d'
    table = client.query(query=query, database=app.config["INFLUX_BUCKET"], language="influxql")

    df = table.select(['time', 'latitude', 'longitude', 'altitude', 'solarEnergy']) \
        .to_pandas() \
        .sort_values(by="time")

    return df.to_json(orient="records")


@app.route("/api/positions")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def api_positions():
    """Render a positions JSON"""
#    query = "select * from telemetry GROUP BY car"
    query = """\
SELECT LAST(latitude),latitude,longitude,*
FROM "telemetry"
WHERE
time >= now() - 1d
GROUP BY shortname"""

    table = client.query(query=query, database=app.config["INFLUX_BUCKET"], language="influxql")

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
        df = []
        center = {
            "lat": -25.0,
            "lng": 130.0,
        }
    else:
        center = {
            "lat": df["latitude"].mean(),
            "lng": df["longitude"].mean(),
        }

    # We're in 2023 and this the best Python can do?
    items = json.loads(df.to_json(orient="records"))

    return json.dumps({
        "center": center,
        "items": items,
    }, ignore_nan=True)
