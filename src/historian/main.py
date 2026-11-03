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

from .config import ConfigError, require_env
from .influx_writer import InfluxWriter
from .modbus_reader import read_tag
from .read_policy import read_cycle
from .write_policy import WriteGate
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


def build_historian_config(mapping_doc: dict[str, Any], entry: dict[str, Any]) -> tuple[str, dict[str, str]]:
    defaults = mapping_doc.get("defaults", {})
    default_historian = defaults.get("historian", {})
    historian = entry.get("historian", {})

    measurement = historian.get("measurement", default_historian.get("measurement", "historian_semantic"))
    tags = historian.get("tags", {})

    return measurement, tags


def main() -> None:
    cfg_path = os.environ.get("HISTORIAN_TAGS", "./tags.yaml")
    modbus_host = os.environ.get("MODBUS_HOST", "plc")
    modbus_port = int(os.environ.get("MODBUS_PORT", "502"))
    poll_interval = float(os.environ.get("POLL_INTERVAL", "1.0"))

    influx_url = os.environ.get("INFLUX_URL", "http://influxdb:8086")
    try:
        influx_token = require_env(os.environ, "INFLUX_TOKEN")
    except ConfigError as ex:
        struct_log("error", "config.invalid", error=str(ex))
        raise SystemExit(1)
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

    def log_read_failure(tag: Any, attempt: int, ex: Exception) -> None:
        struct_log(
            "warning",
            "read.failed",
            tag=tag.name,
            attempt=attempt,
            error=str(ex),
        )

    try:
        while True:
            cycle_ts = datetime.now(timezone.utc)
            cycle_values: dict[str, dict[str, Any]] = {}
            reads_skipped = 0
            write_gate = WriteGate()

            # read_cycle corta el ciclo si un tag agota sus reintentos por excepción
            # (PLC caído): los tags que faltan no se intentan. Ver spec 003.
            for tag, result in read_cycle(
                lambda t: read_tag(mb_client, t), tags, on_failure=log_read_failure
            ):
                value = result.value
                attempts = result.attempts
                quality = "GOOD"

                if value is None:
                    cycle_values[tag.name] = {
                        "value": None,
                        "timestamp": cycle_ts.isoformat(),
                        "quality": "BAD",
                        "source": source_name,
                        "attempts": attempts,
                    }
                    if result.skipped:
                        reads_skipped += 1
                        cycle_values[tag.name]["reason"] = "plc_unreachable"
                    struct_log("warning", "value.missing", tag=tag.name)
                    continue

                cycle_values[tag.name] = {
                    "value": value,
                    "timestamp": cycle_ts.isoformat(),
                    "quality": quality,
                    "source": source_name,
                    "attempts": attempts,
                }

                mapping_entry = mapping_index.get(tag.name)
                if mapping_entry is None:
                    struct_log("warning", "mapping.missing_for_tag", tag=tag.name)
                    continue

                measurement, historian_tags = build_historian_config(mapping_doc, mapping_entry)
                field_name = mapping_entry["name"]

                def log_write_failure(attempt: int, ex: Exception, tag_name: str = tag.name) -> None:
                    struct_log(
                        "warning",
                        "influx.write_retry",
                        tag=tag_name,
                        attempt=attempt,
                        error=str(ex),
                    )

                # La escritura se reintenta ante errores transitorios; si InfluxDB no
                # responde, las demás de este ciclo se saltan. Ver spec 004.
                write_result = write_gate.write(
                    lambda: influx_writer.write_value(
                        measurement=measurement,
                        field_name=field_name,
                        value=value,
                        ts=cycle_ts,
                        tags=historian_tags,
                    ),
                    on_failure=log_write_failure,
                )
                if write_result.ok:
                    struct_log(
                        "info",
                        "point.written",
                        tag=tag.name,
                        measurement=measurement,
                        field=field_name,
                        value=value,
                        quality=quality,
                        source=source_name,
                    )
                else:
                    cycle_values[tag.name]["quality"] = "INFLUX_WRITE_FAILED"
                    if write_result.skipped:
                        cycle_values[tag.name]["reason"] = "influx_unreachable"
                    struct_log(
                        "error",
                        "influx.write_failed",
                        tag=tag.name,
                        attempts=write_result.attempts,
                        skipped=write_result.skipped,
                        error=str(write_result.error) if write_result.error else None,
                    )

            if write_gate.skipped:
                struct_log(
                    "warning",
                    "cycle.writes_skipped",
                    skipped=write_gate.skipped,
                    reason="influx_unreachable",
                )

            if reads_skipped:
                struct_log(
                    "warning",
                    "cycle.reads_skipped",
                    skipped=reads_skipped,
                    reason="plc_unreachable",
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