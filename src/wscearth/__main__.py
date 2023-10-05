"""Main entry point for executing wscearth as a module via python3 -m wscearth"""

import wscearth

wscearth.app.run(debug=True, host="0.0.0.0", port=8080)
