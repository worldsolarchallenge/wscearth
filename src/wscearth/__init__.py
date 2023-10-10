"""WSC Earth is a flask app which renders a map of the current car positions."""

from flask import Flask
from flask_caching import Cache

config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

import wscearth.views # pylint: disable=wrong-import-position

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
