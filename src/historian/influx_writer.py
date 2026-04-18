from __future__ import annotations

from datetime import datetime
from typing import Any

from influxdb_client import InfluxDBClient, Point, WritePrecision
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
        field_name: str,
        value: Any,
        ts: datetime,
        tags: dict[str, str] | None = None,
    ) -> None:
        point = Point(measurement)

        if tags:
            for k, v in tags.items():
                if v is not None:
                    point = point.tag(k, str(v))

        if isinstance(value, bool):
            point = point.field(field_name, value)
        elif isinstance(value, int):
            point = point.field(field_name, value)
        elif isinstance(value, float):
            point = point.field(field_name, value)
        else:
            point = point.field(field_name, str(value))

        point = point.time(ts, WritePrecision.NS)

        self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def close(self) -> None:
        self.client.close()