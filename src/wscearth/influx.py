"""influx tools for wscearth"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class WSCInflux:
    """A class for implementing useful interactions with influxdb"""

    def __init__(self, client):
        self.client = client

    def get_paths(self, measurement="telemetry", shortname="", external_only=True):
        """Get the path of each car. This could be a large table."""
        query = f"""
SELECT *
FROM \"{measurement}\"
WHERE shortname = '{shortname}' AND
{"class <> 'Official Vehicles' AND " if external_only else ""}
time >= -30d"""
        table = self.client.query(query=query, language="influxql")

        df = (
            table.select(["time", "latitude", "longitude", "altitude", "solarEnergy"])
            .to_pandas()
            .sort_values(by="time")
        )

        logger.debug(df)
        return df

    def get_positions(self, measurement="telemetry", timing_measurement="timingsheet", external_only=True):
        """Get the most recent position information from each car."""

        trailering_query = f"""\
    SELECT MAX(trailering)
    FROM "{timing_measurement}"
    WHERE
    class <> 'Other' AND
    {"class <> 'Official Vehicles' AND " if external_only else ""}
    time >= now() - 7d
    GROUP BY shortname"""  # pylint: disable=duplicate-code
        trailering_table = self.client.query(query=trailering_query, language="influxql")

        # Convert to dataframe
        trailering_df = pd.DataFrame()
        if len(trailering_table) > 0:
            trailering_df = (
                trailering_table.to_pandas()
                .reset_index()
                .rename(columns={"max": "trailering"})
                [["shortname","trailering"]]
            )
            # print(trailering_df[["shortname","trailering"]])

        query = f"""\
SELECT LAST(latitude),latitude,longitude,*
FROM "{measurement}"
WHERE
class <> 'Other' AND
{"class <> 'Official Vehicles' AND " if external_only else ""}
time >= now() - 10h
GROUP BY shortname"""  # pylint: disable=duplicate-code

        table = self.client.query(query=query, language="influxql")

        # Convert to dataframe
        df = (table.to_pandas()
            .sort_values(by="time")
        )
        df["trailering"] = False

        if not trailering_df.empty:
            df = (df
                .drop(columns=["trailering"])
                .merge(trailering_df, on="shortname", how="left", suffixes=("_original",None))
            )
        return df
