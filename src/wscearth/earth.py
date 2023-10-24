"""Render a KML file of the WSC event"""
import logging
import datetime

import flask
import flask_cachecontrol
from influxdb_client_3 import InfluxDBClient3
import pandas as pd
import pytz
import simplekml

import wscearth.influx

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app, cache  # pylint: disable=cyclic-import

logger = logging.getLogger(__name__)

# Create an InfluxDB client object. It may make sense to have the app own this.
client = InfluxDBClient3(
    host=app.config["INFLUX_URL"],
    token=app.config["INFLUX_TOKEN"],
    org=app.config["INFLUX_ORG"],
    database=app.config["INFLUX_BUCKET"],
)

wsc_influx = wscearth.influx.WSCInflux(client)


@app.route("/latest.kml")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def latestkml():
    """Render a KML of the event"""

    positions = wsc_influx.get_positions(measurement=app.config["INFLUX_MEASUREMENT"],
                                         external_only=app.config["EXTERNAL_ONLY"])

    kml = simplekml.Kml()
    kml.document = None  # Removes the default document
    kml.resetidcounter()
    expire_time = pytz.utc.localize(datetime.datetime.utcnow())
    expire_time = expire_time + datetime.timedelta(seconds=30)
    kml.networklinkcontrol.expires = expire_time.isoformat()

    # FIXME: Should some of this come from Karma Bunny? # pylint: disable=fixme
    icons = {
        "Challenger": {
            "href": "https://maps.google.com/mapfiles/kml/paddle/grn-blank.png",
            "scale": 2.0,
            "hotspot": (0.5, 0),
        },
        "Cruiser": {
            "href": "https://maps.google.com/mapfiles/kml/paddle/purple-blank.png",
            "scale": 2.0,
            "hotspot": (0.5, 0),
        },
        "Adventure": {
            "href": "https://maps.google.com/mapfiles/kml/paddle/blu-stars.png",
            "scale": 2.0,
            "hotspot": (0.5, 0),
        },
        "Trailered": {
            "href": "https://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
            "scale": 1.0,
            "hotspot": (0.5, 0),
        },
        "Official Vehicles": {
            "href": "https://maps.google.com/mapfiles/kml/paddle/ylw-stars.png",
            "scale": 2.0,
            "hotspot": (0.5, 0),
        },
    }

    def _set_icon(pnt, name):
        if not name in icons:
            return
        if "href" in icons[name]:
            pnt.style.iconstyle.icon.href = icons[name]["href"]
        if "scale" in icons[name]:
            pnt.style.iconstyle.scale = icons[name]["scale"]
        if "hotspot" in icons[name]:
            hotx, hoty = icons[name]["hotspot"]
            pnt.style.iconstyle.hotspot = simplekml.HotSpot(
                x=hotx, y=hoty, xunits=simplekml.Units.fraction, yunits=simplekml.Units.fraction
            )

    folders = {}

    for _, row in positions.sort_values(by="teamnum").iterrows():
        trailered = False
        carclass = row["class"]

        if "trailering" in row.keys():
            trailered = row["trailering"]

        if carclass != "Official Vehicles" and trailered:
            folder_name = "Trailered"
        else:
            folder_name = carclass

        if folder_name not in folders:
            folders[folder_name] = kml.newfolder(name=folder_name)

        pnt = folders[folder_name].newpoint()
        pnt.name = f"{row['teamnum']} - {row['shortname']}"
        pnt.coords = [(row["longitude"], row["latitude"])]

        if "time" not in row.keys():
            logger.error("SHould have time in %s", row)

        description = f"""\
{f"Speed: {row['speed']:.1f} km/h" if "speed" in row else ""}
{f"Driven: {row['distance']:.1f} km" if "distance" in row else ""}
{f"Last Update: {((pd.Timestamp.now() - row['time']).total_seconds())/60.0:.1f} min ago"}
"""
        pnt.description = description

        _set_icon(pnt, folder_name)

    logger.debug("Outputting kml: '%s'", kml.kml())
    return flask.Response(kml.kml(), mimetype="application/vnd.google-earth.kml+xml")


@app.route("/earth.kml")
@cache.cached()
def earthkml():
    """Implement a wrapper KML which references the above"""
    kml = simplekml.Kml(name="Bridgestone World Solar Challenge", open=1)

    netlink = kml.newnetworklink(name="Route")
    netlink.link.href = app.url_for("routekml", _external=True)
    netlink.visibility = 1

    netlink = kml.newnetworklink(name="Latest Positions")
    netlink.link.href = app.url_for("latestkml", _external=True)
    netlink.link.refreshmode = simplekml.RefreshMode.oninterval
    netlink.link.refreshinterval = 10.0
    netlink.visibility = 1

    return flask.Response(kml.kml(), mimetype="application/vnd.google-earth.kml+xml")
