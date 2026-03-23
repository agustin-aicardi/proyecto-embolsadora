from __future__ import annotations

from datetime import datetime
from typing import Any

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.bucket = bucket
        self.org = org
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def write_value(
        self,
        measurement: str,
        tag_name: str,
        value: Any,
        ts: datetime,
    ) -> None:
        point = Point(measurement).tag("tag", tag_name).field(tag_name, value).time(ts)
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def close(self) -> None:
        self.client.close()