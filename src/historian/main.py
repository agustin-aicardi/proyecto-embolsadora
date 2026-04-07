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
from .aas_updater import AASUpdater

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

    aas_xml_path = os.environ.get("AAS_XML_PATH")
    aas_mapping_path = os.environ.get("AAS_MAPPING_PATH")
    aas_output_path = os.environ.get("AAS_OUTPUT_PATH")

    tags = load_tags(cfg_path)

    influx_writer = InfluxWriter(
        url=influx_url,
        token=influx_token,
        org=influx_org,
        bucket=influx_bucket,
    )

    aas_updater = None
    if aas_xml_path and aas_mapping_path and aas_output_path:
        aas_updater = AASUpdater(
            aas_xml_path=aas_xml_path,
            mapping_path=aas_mapping_path,
            tags_path=cfg_path,
        )
        struct_log(
            "info",
            "aas.updater_initialized",
            output_path=aas_output_path,
            mapping_path=aas_mapping_path,
            tags_path=cfg_path,
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
        source_name = "mock_modbus"
        struct_log("info", "modbus.using_mock")
    else:
        mb_client = ModbusTcpClient(host=modbus_host, port=modbus_port)
        source_name = "modbus_tcp"

    try:
        connected = mb_client.connect()
        if not connected:
            struct_log(
                "warning",
                "modbus.connect_failed",
                host=modbus_host,
                port=modbus_port,
            )
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
            cycle_values: dict[str, dict[str, Any]] = {}

            for tag in tags:
                attempts = 0
                value = None
                quality = "BAD"

                while attempts < 3:
                    try:
                        value = read_tag(mb_client, tag)
                        quality = "GOOD"
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
                    cycle_values[tag.name] = {
                        "value": None,
                        "timestamp": cycle_ts.isoformat(),
                        "quality": "BAD",
                        "source": source_name,
                        "attempts": attempts,
                    }
                    struct_log("warning", "value.missing", tag=tag.name)
                    continue

                # Mantengo compatibilidad con el comportamiento anterior:
                # los bool se escriben a Influx y AAS como 1/0.
                if tag.type == "bool":
                    value = 1 if value else 0

                cycle_values[tag.name] = {
                    "value": value,
                    "timestamp": cycle_ts.isoformat(),
                    "quality": quality,
                    "source": source_name,
                    "attempts": attempts,
                }

                try:
                    influx_writer.write_value(
                        measurement="historian_measurement",
                        tag_name=tag.name,
                        value=value,
                        ts=cycle_ts,
                    )
                    struct_log(
                        "info",
                        "point.written",
                        tag=tag.name,
                        value=value,
                        quality=quality,
                        source=source_name,
                    )
                except Exception as ex:
                    cycle_values[tag.name]["quality"] = "INFLUX_WRITE_FAILED"
                    struct_log(
                        "error",
                        "influx.write_failed",
                        tag=tag.name,
                        error=str(ex),
                    )

            if aas_updater is not None:
                aas_values = {
                    tag_name: meta["value"]
                    for tag_name, meta in cycle_values.items()
                    if meta["value"] is not None and meta["quality"] == "GOOD"
                }

                if aas_values:
                    try:
                        updated_tags = aas_updater.update_from_dict(aas_values)
                        aas_updater.save(aas_output_path)
                        struct_log(
                            "info",
                            "aas.updated",
                            updated_tags=updated_tags,
                            output_path=aas_output_path,
                        )
                    except Exception as ex:
                        struct_log("error", "aas.update_failed", error=str(ex))

            struct_log(
                "info",
                "cycle.completed",
                tags_total=len(tags),
                tags_ok=len([v for v in cycle_values.values() if v["quality"] == "GOOD"]),
                tags_bad=len([v for v in cycle_values.values() if v["quality"] != "GOOD"]),
            )

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