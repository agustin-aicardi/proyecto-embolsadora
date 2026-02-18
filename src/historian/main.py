"""Historian service: read tags from YAML, read Modbus, write to InfluxDB."""
from __future__ import annotations

import os
import time
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict

import yaml
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from pymodbus.client import ModbusTcpClient
try:
    # local mock for integration tests
    from .mock_modbus import MockModbusClient
except Exception:
    MockModbusClient = None
from .parsers import int16_from_register, float32_from_registers, bool_from_bits

# Load environment from .env if present
load_dotenv()

LOG = logging.getLogger("historian")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
LOG.addHandler(handler)
LOG.setLevel(logging.INFO)


def struct_log(level: str, msg: str, **fields: Any) -> None:
    payload = {"ts": datetime.utcnow().isoformat() + "Z", "level": level, "msg": msg}
    payload.update(fields)
    LOG.log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload))


def load_tags(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def read_bool(client: ModbusTcpClient, unit: int, address: int) -> bool | None:
    rr = client.read_coils(address, 1, unit=unit)
    if rr is None or not hasattr(rr, "bits"):
        return None
    return bool_from_bits(rr.bits)


def read_int16(client: ModbusTcpClient, unit: int, address: int) -> int | None:
    rr = client.read_holding_registers(address, 1, unit=unit)
    if rr is None or not hasattr(rr, "registers"):
        return None
    val = rr.registers[0]
    return int16_from_register(val)


def read_float32(client: ModbusTcpClient, unit: int, address: int, byteorder: str = "big") -> float | None:
    rr = client.read_holding_registers(address, 2, unit=unit)
    if rr is None or not hasattr(rr, "registers"):
        return None
    hi, lo = rr.registers[0], rr.registers[1]
    return float32_from_registers(hi, lo, byteorder=byteorder)


def write_point(write_api, bucket: str, org: str, measurement: str, tag_name: str, value: Any, ts: datetime):
    p = Point(measurement).tag("tag", tag_name).field("value", value).time(ts)
    write_api.write(bucket=bucket, org=org, record=p)


def main():
    cfg_path = os.environ.get("HISTORIAN_TAGS", "./tags.yaml")
    modbus_host = os.environ.get("MODBUS_HOST", "plc")
    modbus_port = int(os.environ.get("MODBUS_PORT", "502"))
    poll_interval = float(os.environ.get("POLL_INTERVAL", "1.0"))

    influx_url = os.environ.get("INFLUX_URL", "http://influxdb:8086")
    influx_token = os.environ.get("INFLUX_TOKEN", "my-token")
    influx_org = os.environ.get("INFLUX_ORG", "org")
    influx_bucket = os.environ.get("INFLUX_BUCKET", "bucket")

    tags_doc = load_tags(cfg_path)
    tags = tags_doc.get("tags", [])

    # prepare Influx client
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    struct_log("info", "historian.started", modbus_host=modbus_host, modbus_port=modbus_port, tags=len(tags))

    # Support a mock modbus client for integration tests by setting MODBUS_HOST=mock
    if modbus_host == "mock" and MockModbusClient is not None:
        mb_client = MockModbusClient(host=modbus_host, port=modbus_port)
        struct_log("info", "modbus.using_mock")
    else:
        mb_client = ModbusTcpClient(host=modbus_host, port=modbus_port)
    try:
        connected = mb_client.connect()
        if not connected:
            struct_log("warning", "modbus.connect_failed", host=modbus_host, port=modbus_port)
    except Exception:
        struct_log("warning", "modbus.connect_exception", host=modbus_host, port=modbus_port)

    try:
        while True:
            cycle_ts = datetime.now(timezone.utc)
            for t in tags:
                name = t.get("name")
                unit_id = int(t.get("unit", 1))
                address = int(t.get("address"))
                ttype = t.get("type")
                byteorder = t.get("byteorder", "big")

                # retry policy: 3 attempts, 5s between attempts
                attempts = 0
                value = None
                while attempts < 3:
                    try:
                        if ttype == "bool":
                            value = read_bool(mb_client, unit_id, address)
                        elif ttype == "int16":
                            value = read_int16(mb_client, unit_id, address)
                        elif ttype == "float32":
                            value = read_float32(mb_client, unit_id, address, byteorder=byteorder)
                        else:
                            struct_log("error", "unsupported.type", tag=name, type=ttype)
                            break
                        break
                    except Exception as ex:
                        attempts += 1
                        struct_log("warning", "read.failed", tag=name, attempt=attempts, error=str(ex))
                        time.sleep(5)

                if value is None:
                    struct_log("warning", "value.missing", tag=name)
                    continue

                try:
                    write_point(write_api, influx_bucket, influx_org, "historian_measurement", name, value, cycle_ts)
                    struct_log("info", "point.written", tag=name, value=value)
                except Exception as ex:
                    struct_log("error", "influx.write_failed", tag=name, error=str(ex))

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        struct_log("info", "historian.stopped")
    finally:
        try:
            mb_client.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
