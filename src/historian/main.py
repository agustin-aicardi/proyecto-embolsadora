"""Historian service: load tags, read Modbus, write to InfluxDB."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient

from .influx_writer import InfluxWriter
from .modbus_reader import read_tag
from .tag_loader import load_tags

try:
    from .mock_modbus import MockModbusClient
except Exception:
    MockModbusClient = None


load_dotenv()

LOG = logging.getLogger("historian")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
LOG.addHandler(handler)
LOG.setLevel(logging.INFO)


def struct_log(level: str, msg: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "msg": msg,
    }
    payload.update(fields)
    LOG.log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload))


def main() -> None:
    cfg_path = os.environ.get("HISTORIAN_TAGS", "./tags.yaml")
    modbus_host = os.environ.get("MODBUS_HOST", "plc")
    modbus_port = int(os.environ.get("MODBUS_PORT", "502"))
    poll_interval = float(os.environ.get("POLL_INTERVAL", "1.0"))

    influx_url = os.environ.get("INFLUX_URL", "http://influxdb:8086")
    influx_token = os.environ.get("INFLUX_TOKEN", "my-token")
    influx_org = os.environ.get("INFLUX_ORG", "org")
    influx_bucket = os.environ.get("INFLUX_BUCKET", "bucket")

    tags = load_tags(cfg_path)

    influx_writer = InfluxWriter(
        url=influx_url,
        token=influx_token,
        org=influx_org,
        bucket=influx_bucket,
    )

    struct_log(
        "info",
        "historian.started",
        modbus_host=modbus_host,
        modbus_port=modbus_port,
        tags=len(tags),
    )

    if modbus_host == "mock" and MockModbusClient is not None:
        mb_client = MockModbusClient(host=modbus_host, port=modbus_port)
        struct_log("info", "modbus.using_mock")
    else:
        mb_client = ModbusTcpClient(host=modbus_host, port=modbus_port)

    try:
        connected = mb_client.connect()
        if not connected:
            struct_log("warning", "modbus.connect_failed", host=modbus_host, port=modbus_port)
    except Exception as ex:
        struct_log(
            "warning",
            "modbus.connect_exception",
            host=modbus_host,
            port=modbus_port,
            error=str(ex),
        )

    try:
        while True:
            cycle_ts = datetime.now(timezone.utc)

            for tag in tags:
                attempts = 0
                value = None

                while attempts < 3:
                    try:
                        value = read_tag(mb_client, tag)
                        break
                    except Exception as ex:
                        attempts += 1
                        struct_log(
                            "warning",
                            "read.failed",
                            tag=tag.name,
                            attempt=attempts,
                            error=str(ex),
                        )
                        time.sleep(5)

                if value is None:
                    struct_log("warning", "value.missing", tag=tag.name)
                    continue

                if tag.type == "bool":
                    value = 1 if value else 0

                try:
                    influx_writer.write_value(
                        measurement="historian_measurement",
                        tag_name=tag.name,
                        value=value,
                        ts=cycle_ts,
                    )
                    struct_log("info", "point.written", tag=tag.name, value=value)
                except Exception as ex:
                    struct_log("error", "influx.write_failed", tag=tag.name, error=str(ex))

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        struct_log("info", "historian.stopped")
    finally:
        try:
            mb_client.close()
        except Exception:
            pass
        try:
            influx_writer.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()