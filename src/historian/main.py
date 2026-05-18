"""Historian service: load tags, read Modbus, write to InfluxDB."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import yaml
from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient

from .influx_writer import InfluxWriter
from .modbus_reader import read_tag, ReadResult
from .tag_loader import load_tags
from .aas_updater import AASUpdater
from .basyx_updater import BaSyxUpdater

try:
    from .mock_modbus import MockModbusClient
except Exception:
    MockModbusClient = None

load_dotenv()

basyx_url = os.environ.get("BASYX_URL")

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


def load_mapping(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_mapping_index(mapping_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mappings = mapping_doc.get("mappings", [])
    index: dict[str, dict[str, Any]] = {}

    for entry in mappings:
        if not entry.get("enabled", True):
            continue
        name = entry["name"]
        index[name] = entry

    return index


def build_historian_config(
    mapping_doc: dict[str, Any],
    entry: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    defaults = mapping_doc.get("defaults", {})
    default_historian = defaults.get("historian", {})
    historian = entry.get("historian", {})

    measurement = historian.get(
        "measurement",
        default_historian.get("measurement", "historian_semantic"),
    )
    tags = historian.get("tags", {})

    return measurement, tags


def main() -> None:
    cfg_path = os.environ.get("HISTORIAN_TAGS", "./tags.yaml")
    modbus_host = os.environ.get("MODBUS_HOST", "plc")
    modbus_port = int(os.environ.get("MODBUS_PORT", "502"))
    poll_interval = float(os.environ.get("POLL_INTERVAL", "1.0"))

    heartbeat_tag_name = os.environ.get("HEARTBEAT_TAG_NAME", "heartbeat")
    heartbeat_timeout = float(os.environ.get("HEARTBEAT_TIMEOUT", "5.0"))
    last_heartbeat_value = None
    last_heartbeat_change_ts = None

    influx_url = os.environ.get("INFLUX_URL", "http://influxdb:8086")
    influx_token = os.environ.get("INFLUX_TOKEN", "my-token")
    influx_org = os.environ.get("INFLUX_ORG", "org")
    influx_bucket = os.environ.get("INFLUX_BUCKET", "bucket")

    aas_xml_path = os.environ.get("AAS_XML_PATH")
    aas_mapping_path = os.environ.get("AAS_MAPPING_PATH")
    aas_output_path = os.environ.get("AAS_OUTPUT_PATH")

    tags = load_tags(cfg_path)

    mapping_doc: dict[str, Any] = {}
    mapping_index: dict[str, dict[str, Any]] = {}

    if aas_mapping_path:
        mapping_doc = load_mapping(aas_mapping_path)
        mapping_index = build_mapping_index(mapping_doc)

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

    basyx_updater = None
    if basyx_url and aas_xml_path and mapping_doc:
        basyx_updater = BaSyxUpdater(
            base_url=basyx_url,
            aas_xml_path=aas_xml_path,
            mapping_doc=mapping_doc,
        )
        struct_log(
            "info",
            "basyx.updater_initialized",
            basyx_url=basyx_url,
        )

    struct_log(
        "info",
        "historian.started",
        modbus_host=modbus_host,
        modbus_port=modbus_port,
        tags=len(tags),
        heartbeat_tag=heartbeat_tag_name,
        heartbeat_timeout=heartbeat_timeout,
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
                result = ReadResult(
                    value=None,
                    quality="BAD",
                    reason="not_read",
                )

                while attempts < 3:
                    attempts += 1

                    try:
                        result = read_tag(mb_client, tag)

                        if result.quality == "GOOD":
                            break

                        struct_log(
                            "warning",
                            "read.invalid",
                            tag=tag.name,
                            attempt=attempts,
                            quality=result.quality,
                            reason=result.reason,
                        )

                    except Exception as ex:
                        result = ReadResult(
                            value=None,
                            quality="BAD",
                            reason="read_exception",
                        )
                        struct_log(
                            "warning",
                            "read.failed",
                            tag=tag.name,
                            attempt=attempts,
                            error=str(ex),
                        )

                    time.sleep(0.2)

                value = result.value
                quality = result.quality
                reason = result.reason

                if tag.name == heartbeat_tag_name and quality == "GOOD":
                    if last_heartbeat_value is None or value != last_heartbeat_value:
                        last_heartbeat_value = value
                        last_heartbeat_change_ts = cycle_ts

                        struct_log(
                            "info",
                            "heartbeat.changed",
                            tag=tag.name,
                            value=value,
                        )

                    elif last_heartbeat_change_ts is not None:
                        seconds_since_change = (
                            cycle_ts - last_heartbeat_change_ts
                        ).total_seconds()

                        if seconds_since_change > heartbeat_timeout:
                            quality = "STALE"
                            reason = "heartbeat_not_changing"

                            struct_log(
                                "warning",
                                "heartbeat.stale",
                                tag=tag.name,
                                value=value,
                                seconds_since_change=seconds_since_change,
                                timeout=heartbeat_timeout,
                            )

                cycle_values[tag.name] = {
                    "value": value,
                    "timestamp": cycle_ts.isoformat(),
                    "quality": quality,
                    "reason": reason,
                    "source": source_name,
                    "attempts": attempts,
                }

                if value is None or quality != "GOOD":
                    struct_log(
                        "warning",
                        "value.invalid",
                        tag=tag.name,
                        quality=quality,
                        reason=reason,
                        attempts=attempts,
                        source=source_name,
                    )
                    continue

                mapping_entry = mapping_index.get(tag.name)
                if mapping_entry is None:
                    struct_log("warning", "mapping.missing_for_tag", tag=tag.name)
                    continue

                measurement, historian_tags = build_historian_config(
                    mapping_doc,
                    mapping_entry,
                )
                field_name = mapping_entry["name"]

                try:
                    influx_writer.write_value(
                        measurement=measurement,
                        field_name=field_name,
                        value=value,
                        ts=cycle_ts,
                        tags=historian_tags,
                    )
                    struct_log(
                        "info",
                        "point.written",
                        tag=tag.name,
                        measurement=measurement,
                        field=field_name,
                        value=value,
                        quality=quality,
                        reason=reason,
                        source=source_name,
                    )
                except Exception as ex:
                    cycle_values[tag.name]["quality"] = "INFLUX_WRITE_FAILED"
                    cycle_values[tag.name]["reason"] = "influx_write_failed"
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

                    if basyx_updater is not None:
                        try:
                            basyx_updated = basyx_updater.update_from_dict(aas_values)
                            struct_log(
                                "info",
                                "basyx.updated",
                                updated_tags=basyx_updated,
                                basyx_url=basyx_url,
                            )
                        except Exception as ex:
                            struct_log("error", "basyx.update_failed", error=str(ex))

            struct_log(
                "info",
                "cycle.completed",
                tags_total=len(tags),
                tags_ok=len(
                    [v for v in cycle_values.values() if v["quality"] == "GOOD"]
                ),
                tags_bad=len(
                    [v for v in cycle_values.values() if v["quality"] != "GOOD"]
                ),
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