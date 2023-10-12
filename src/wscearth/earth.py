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
from wscearth import app,cache # pylint: disable=cyclic-import

logger = logging.getLogger(__name__)

# Create an InfluxDB client object. It may make sense to have the app own this.
client = InfluxDBClient3(host=app.config["INFLUX_URL"],
                         token=app.config["INFLUX_TOKEN"],
                         org=app.config["INFLUX_ORG"],
                         database=app.config["INFLUX_BUCKET"])

wsc_influx = wscearth.influx.WSCInflux(client)

@app.route("/earth/latest.kml")
@cache.cached(timeout=30)
@flask_cachecontrol.cache_for(seconds=30)
def latestkml():
    """Render a KML of the event"""

    positions = wsc_influx.get_positions()

    kml = simplekml.Kml()
    kml.document = None  # Removes the default document
    expire_time = pytz.utc.localize(datetime.datetime.utcnow())
    expire_time = expire_time + datetime.timedelta(seconds=30)
    kml.networklinkcontrol.expires = expire_time.isoformat()

    # FIXME: Should some of this come from Karma Bunny? # pylint: disable=fixme
    icons = {
        "Challenger":{
            "href": "http://maps.google.com/mapfiles/kml/paddle/purple-circle.png",
            "scale": 2.0,
            "hotspot": (0.5,0)
        },
        "Cruiser":{
            "href": "http://maps.google.com/mapfiles/kml/paddle/blu-blank.png",
            "scale": 2.0,
            "hotspot": (0.5,0)
        },
        "Adventure":{
            "href": "http://maps.google.com/mapfiles/kml/paddle/blu-stars.png",
            "scale": 2.0,
            "hotspot": (0.5,0)
        },
        "Trailered":{
            "href": "http://maps.google.com/mapfiles/kml/paddle/grn-blank.png",
            "scale": 1.0,
            "hotspot": (0.5,0)
        },
        "Official Vehicles":{
            "href": "http://maps.google.com/mapfiles/kml/shapes/caution.png",
            "scale": 1.0,
            "hotspot": (0,0)
        },
    }

    def _set_icon(pnt, name):
        if "href" in icons[name]:
            pnt.style.iconstyle.icon.href = icons[name]["href"]
        if "scale" in icons[name]:
            pnt.style.iconstyle.scale = icons[name]["scale"]
        if "hotspot" in icons[name]:
            hotx,hoty = icons[name]["hotspot"]
            pnt.style.iconstyle.hotspot = \
                simplekml.HotSpot(
                    x=hotx,
                    y=hoty,
                    xunits=simplekml.Units.fraction,
                    yunits=simplekml.Units.fraction)

    folders = {}

    for _,row in positions.iterrows():
        trailered = False
        carclass = row["class"]
        if trailered:
            folder_name = "Trailered"
        else:
            folder_name = carclass

        if folder_name not in folders:
            folders[folder_name] = kml.newfolder(name=folder_name)

        pnt = folders[folder_name].newpoint()
        pnt.name = f"{row['teamnum']} - {row['shortname']}"
        pnt.coords = [(row["longitude"],row["latitude"])]

        description = f"""\
{f"Speed: {row['speed']:.1f} km/h" if "speed" in row else ""}
{f"Driven: {row['distance']:.1f} km" if "distance" in row else ""}
{f"Last Update: {pd.Timestamp.now() - row['time']} ago"}
"""
        pnt.description = description

        _set_icon(pnt, folder_name)

        logger.critical(row)

    logger.debug("Outputting kml: '%s'", kml.kml())
    return flask.Response(kml.kml(), mimetype='application/vnd.google-earth.kml+xml')

@app.route("/earth/earth.kml")
@cache.cached()
def earthkml():
    """Implement a wrapper KML which references the above"""
    kml = simplekml.Kml(name="Bridgestone World Solar Challenge")
    netlink = kml.newnetworklink(name="Latest Positions")
    netlink.refreshvisibility = 0
    netlink.link.href = app.url_for('latestkml', _external=True)
    netlink.link.viewrefreshmode = simplekml.RefreshMode.oninterval
    netlink.link.refreshmode = 10.0
    netlink.visibility = 1

    return flask.Response(kml.kml(), mimetype='application/vnd.google-earth.kml+xml')