# pylint: disable=duplicate-code
"""Basic app endpoints for wscearth"""

import flask
import flask_cachecontrol
from influxdb_client_3 import InfluxDBClient3
import simplejson as json

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app, cache  # pylint: disable=cyclic-import

client = InfluxDBClient3(
    host=app.config["INFLUX_URL"],
    token=app.config["INFLUX_TOKEN"],
    org=app.config["INFLUX_ORG"],
    database=app.config["INFLUX_BUCKET"],
)


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


@app.route("/api/path/<teamnum>")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def api_path(teamnum):
    """Render JSON path positions for car"""

    teamnum = int(teamnum)
    query = f'SELECT * FROM "{app.config["measurement"]}" WHERE shortname = {teamnum} and time >= -30d'
    table = client.query(query=query, database=app.config["INFLUX_BUCKET"], language="influxql")

    df = table.select(["time", "latitude", "longitude", "altitude", "solarEnergy"]).to_pandas().sort_values(by="time")

    return df.to_json(orient="records")


@app.route("/api/positions")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def api_positions():
    """Render a positions JSON"""
    #    query = "select * from telemetry GROUP BY car"
    query = f"""\
SELECT LAST(latitude),latitude,longitude,*
FROM "{app.config['INFLUX_MEASUREMENT']}"
WHERE
time >= now() - 1d
GROUP BY shortname"""  # pylint: disable=duplicate-code

    table = client.query(query=query, database=app.config["INFLUX_BUCKET"], language="influxql")

    # Convert to dataframe
    df = table.to_pandas().sort_values(by="time")
    print(df)
    # print(df.to_markdown())

    # lats = []
    # longs = []

    # for row in rows:
    #     lats.append(row["latitude"])
    #     longs.append(row["longitude"])

    # for _,row in df.iterrows():
    #    print(row)

    items = []
    center = {
        "lat": -25.0,
        "lng": 130.0,
    }

    if len(df) > 0:
        items = json.loads(df.to_json(orient="records"))
        center = {
            "lat": df["latitude"].mean(),
            "lng": df["longitude"].mean(),
        }

    return json.dumps(
        {
            "center": center,
            "items": items,
        },
        ignore_nan=True,
    )
