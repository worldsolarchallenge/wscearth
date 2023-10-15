"""influx tools for wscearth"""
import logging

logger = logging.getLogger(__name__)

class WSCInflux:
    """A class for implementing useful interactions with influxdb"""
    def __init__(self, client):
        self.client = client

    def get_paths(self, measurement="telemetry", shortname=""):
        """Get the path of each car. This could be a large table."""
        query = f'SELECT * FROM "{measurement}" WHERE shortname = \'{shortname}\' and time >= -30d'
        table = self.client.query(query=query, language="influxql")

        df = table.select(['time', 'latitude', 'longitude', 'altitude', 'solarEnergy']) \
            .to_pandas() \
            .sort_values(by="time")

        logger.debug(df)
        return df

    def get_positions(self, measurement="telemetry"):
        """Get the most recent position information from each car."""

        query = f"""\
SELECT LAST(latitude),latitude,longitude,*
FROM "{measurement}"
WHERE
time >= now() - 1d
GROUP BY shortname""" # pylint: disable=duplicate-code

        table = self.client.query(query=query, language="influxql")

        # Convert to dataframe
        df = table.to_pandas().sort_values(by="time")

        logger.debug(df)
        return df
