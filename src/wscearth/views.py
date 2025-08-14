# pylint: disable=duplicate-code
"""Basic app endpoints for wscearth"""

import logging

import flask
import flask_cachecontrol
from influxdb_client_3 import InfluxDBClient3
import simplejson as json
import pandas as pd

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app, cache  # pylint: disable=cyclic-import

logger = logging.getLogger(__name__)

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
    query = f"""\
SELECT *
FROM "{app.config["measurement"]}"
WHERE teamnum = {teamnum} AND
{"class <> 'Official Vehicles' AND " if app.config["EXTERNAL_ONLY"] else ""}
time >= -30d"""

    table = client.query(query=query, database=app.config["INFLUX_BUCKET"], language="influxql")

    df = table.select(["time", "latitude", "longitude", "altitude", "solarEnergy"]).to_pandas().sort_values(by="time")

    return df.to_json(orient="records")


@app.route("/api/positions")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def api_positions(sample_data=False):
    """Render a positions JSON"""

    if not sample_data:
        trailering_query = f"""\
    SELECT MAX(trailering)
    FROM "timingsheet"
    WHERE {"class <> 'Official Vehicles' AND " if app.config["EXTERNAL_ONLY"] else ""}
    time >= now() - 7d
    GROUP BY teamnum"""  # pylint: disable=duplicate-code
        trailering_table = client.query(
            query=trailering_query, database=app.config["INFLUX_BUCKET"], language="influxql"
        )
        trailering_df = trailering_table.to_pandas() if trailering_table.num_rows > 0 else pd.DataFrame()
    else:
        # Sample data for testing
        trailering_df = pd.DataFrame({"teamnum": [1, 2, 3], "max": [True, False, True]})

    # Convert to dataframe
    if not trailering_df.empty:
        trailering_df = trailering_df.reset_index().rename(columns={"max": "trailering"})[["teamnum", "trailering"]]

    #    query = "select * from telemetry GROUP BY car"
    query = f"""\
SELECT LAST(latitude),latitude,longitude,*
FROM "{app.config['INFLUX_MEASUREMENT']}"
WHERE class <> 'Other' AND
{"class <> 'Official Vehicles' AND " if app.config["EXTERNAL_ONLY"] else ""}
time >= now() - 10h
GROUP BY teamnum"""  # pylint: disable=duplicate-code

    if not sample_data:
        table = client.query(query=query, database=app.config["INFLUX_BUCKET"], language="influxql")
        # Convert to dataframe
        df = table.to_pandas().sort_values(by="time")
    else:
        # Sample data for testing
        df = pd.DataFrame(
            {
                "team": [
                    "01",
                    "02",
                    "03",
                ],
                "class": ["Challenger", "Cruiser", "Explorer"],
                "teamnum": [1, 2, 3],
                "latitude": [-25.0, -26.0, -27.0],
                "longitude": [130.0, 131.0, 132.0],
                "altitude": [100, 200, 300],
                "solarEnergy": [500, 600, 700],
                "time": pd.date_range(start="2025-08-13", periods=3, freq="H"),
            }
        ).sort_values(by="time")

    df["trailering"] = False

    logger.critical("DF: \n%s", df)
    logger.critical("Trailering: \n%s", trailering_df)

    if not trailering_df.empty:
        df = df.drop(columns=["trailering"]).merge(
            trailering_df, on="teamnum", how="left", suffixes=("_original", None)
        )

    logger.critical("Merged: \n%s", df)

    print(df)

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


@app.route("/api/positions/sample")
def api_positions_sample():
    return api_positions(sample_data=True)
