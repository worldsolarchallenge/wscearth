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
        competing_query = f"""\
    SELECT MIN(Competing)
    FROM "timingsheet"
    WHERE {"class <> 'Official Vehicles' AND " if app.config["EXTERNAL_ONLY"] else ""}
    time >= now() - 7d
    GROUP BY teamnum"""  # pylint: disable=duplicate-code
        competing_table = client.query(
            query=competing_query, database=app.config["INFLUX_BUCKET"], language="influxql"
        )
        competing_df = competing_table.to_pandas() if competing_table.num_rows > 0 else pd.DataFrame()
    else:
        # Sample data for testing
        competing_df = pd.DataFrame({"teamnum": [1, 2, 3], "min": [True, False, True]})

    # Convert to dataframe
    if not competing_df.empty:
        competing_df = competing_df.reset_index().rename(columns={"min": "competing"})[["teamnum", "competing"]]
        competing_df["trailering"] = ~competing_df["competing"]

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
                "car": ["Car 1", "Car 2", "Car 3"],
                "class": ["Challenger", "Cruiser", "Explorer"],
                "distance": [1500.0, 1600.0, 1700.0],
                "teamnum": [1, 2, 3],
                "latitude": [-25.0, -26.0, -27.0],
                "longitude": [130.0, 131.0, 132.0],
                "altitude": [100.0, 200.0, 300.0],
                "avg_speed": [50.0, 60.0, 70.0],
                "event": ["BWSC2025", "BWSC2025", "BWSC2025"],
                "event_hours": [10, 11, 12],
                "messengerId": ["0-3193488", "0-3193489", "0-3193490"],
                "shortname": ["Team 1", "Team 2", "Team 3"],
                "speed": [20.0, 30.0, 40.0],
                "time": pd.date_range(start="2025-08-13", periods=3, freq="H"),
            }
        ).sort_values(by="time")

    df["competing"] = True
    df["trailering"] = False

    logger.critical("DF: \n%s", df)
    logger.critical("Competing: \n%s", competing_df)

    if not competing_df.empty:
        df = df.drop(columns=["competing"]).merge(
            competing_df, on="teamnum", how="left", suffixes=("_original", None)
        )
    else:
        logger.warning("competing_df was empty")

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
    """Return  sample positions data for testing."""
    return api_positions(sample_data=True)
