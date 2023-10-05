"""WSC Earth is a flask app which renders a map of the current car positions."""

from flask import Flask
app = Flask(__name__)

import wscearth.views # pylint: disable=wrong-import-position

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
