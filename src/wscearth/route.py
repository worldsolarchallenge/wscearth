"""Render a KML file of the WSC event"""
import logging
import tempfile

import flask
import flask_cachecontrol

# import flask_cachecontrol
import pandas as pd
import simplekml
import yaml

# Circular import recommended here: https://flask.palletsprojects.com/en/3.0.x/patterns/packages/
from wscearth import app, cache  # pylint: disable=cyclic-import

logger = logging.getLogger(__name__)

# Read the data table from a file called `route.txt`.
route_data = pd.read_table("route.txt")

with open("controlstops.yaml", encoding="utf-8") as f:
    controlstop_data = yaml.safe_load(f)["controlstops"]


def build_route_kml():
    """Render a KMZ of the event route"""

    kml = simplekml.Kml(open=1)
    kml.document = None  # Removes the default document

    coords = []
    for _, point in route_data.iterrows():
        coords.append((point["long"], point["lat"]))
    route = kml.newlinestring(name="Route", description="Bridgestone World Solar Challenge Route", coords=coords)
    route.style.linestyle.width = 5
    route.style.linestyle.color = "FF1c3bb8"

    controlstops = kml.newfolder(name="NRMA Control Stops")
    logger.critical(controlstop_data)
    for _, stop in route_data[route_data["name"].isnull() == False].iterrows():  # pylint: disable=singleton-comparison
        logger.debug("Reading data %s", stop)
        logger.debug("Creating control point %s", stop["name"])
        pnt = controlstops.newpoint(name=stop["name"])
        pnt.coords = [(stop["long"], stop["lat"])]
        pnt.description = f"NRMA Control stop at {stop['km']:.1f} km."  # Teams must want FIXME minutes.

        pnt.style.iconstyle.icon.href = "https://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png"
        pnt.style.iconstyle.scale = 1.0
        pnt.style.iconstyle.hotspot = simplekml.HotSpot(
                x=20, y=2, xunits=simplekml.Units.pixels, yunits=simplekml.Units.pixels
            )

        # pnt.style.iconstyle.icon.href = icons[name]["href"]
        # pnt.style.iconstyle.scale = icons[name]["scale"]
        # pnt.style.iconstyle.hotspot = \
        #     simplekml.HotSpot(
        #         x=hotx,
        #         y=hoty,
        #         xunits=simplekml.Units.fraction,
        #         yunits=simplekml.Units.fraction)

    return kml


@app.route("/route4.kmz")
@cache.cached()
@flask_cachecontrol.cache_for(hours=3)
def routekmz():
    """Serve a KMZ with the route details."""
    kml = build_route_kml()
    logger.critical("About to write temp file")
    with tempfile.NamedTemporaryFile() as t:
        logger.critical("Saving to %s", t.name)
        kml.savekmz(t.name)
        logger.critical("Finished saving to %s", t.name)

        return flask.Response(t.read(), mimetype="application/vnd.google-earth.kmz+xml")


@app.route("/route4.kml")
@cache.cached()
def routekml():
    """Serve a KML with teh route details"""
    kml = build_route_kml()
    return flask.Response(kml.kml(), mimetype="application/vnd.google-earth.kml+xml")

@app.route("/route.json")
@cache.cached()
def routejson():
    """Serve a json route details."""
    return flask.Response(route_data.to_json(orient="records"), mimetype="application/json")
