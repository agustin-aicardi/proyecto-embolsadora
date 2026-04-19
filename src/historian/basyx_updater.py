from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

AAS_NS = {"aas": "https://admin-shell.io/aas/3/0"}


class BaSyxUpdater:
    def __init__(self, base_url: str, aas_xml_path: str, mapping_doc: dict[str, Any]):
        self.base_url = base_url.rstrip("/")
        self.aas_xml_path = Path(aas_xml_path)
        self.mapping_doc = mapping_doc
        self.mappings = mapping_doc.get("mappings", [])
        self.submodel_ids = self._load_submodel_ids()

        self.last_sent_values: dict[str, Any] = {}
        self.float_tolerance = 1e-3

    def _load_submodel_ids(self) -> dict[str, str]:
        tree = ET.parse(self.aas_xml_path)
        root = tree.getroot()

        result: dict[str, str] = {}
        for submodel in root.findall(".//aas:submodel", AAS_NS):
            idshort_el = submodel.find("aas:idShort", AAS_NS)
            id_el = submodel.find("aas:id", AAS_NS)

            if (
                idshort_el is not None
                and idshort_el.text
                and id_el is not None
                and id_el.text
            ):
                result[idshort_el.text.strip()] = id_el.text.strip()

        return result

    @staticmethod
    def _encode_basyx_identifier(identifier: str) -> str:
        raw = identifier.encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _to_aas_string(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _build_idshort_path(aas: dict[str, Any]) -> str:
        parts: list[str] = []
        if aas.get("collection"):
            parts.append(aas["collection"])
        parts.append(aas["property"])
        return ".".join(parts)

    def _has_changed(self, name: str, value: Any) -> bool:
        if name not in self.last_sent_values:
            return True

        previous = self.last_sent_values[name]

        if isinstance(value, bool) or isinstance(previous, bool):
            return value != previous

        if isinstance(value, float) or isinstance(previous, float):
            try:
                return abs(float(value) - float(previous)) > self.float_tolerance
            except (TypeError, ValueError):
                return value != previous

        return value != previous

    def _patch_property_value(
        self,
        submodel_identifier: str,
        idshort_path: str,
        value: Any,
    ) -> None:
        submodel_enc = self._encode_basyx_identifier(submodel_identifier)
        path_enc = urllib.parse.quote(idshort_path, safe=".")

        url = (
            f"{self.base_url}/submodels/"
            f"{submodel_enc}/submodel-elements/{path_enc}/$value"
        )

        payload = json.dumps(self._to_aas_string(value)).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=payload,
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"BaSyx update failed with HTTP {resp.status}")

    def update_from_dict(self, values: dict[str, Any]) -> list[str]:
        updated: list[str] = []

        for mapping in self.mappings:
            if not mapping.get("enabled", True):
                continue

            name = mapping["name"]
            if name not in values:
                continue

            value = values[name]

            if not self._has_changed(name, value):
                continue

            aas = mapping["aas"]
            submodel_idshort = aas["submodel"]

            submodel_identifier = self.submodel_ids.get(submodel_idshort)
            if not submodel_identifier:
                raise KeyError(
                    f"Submodel id not found for idShort '{submodel_idshort}'"
                )

            idshort_path = self._build_idshort_path(aas)

            self._patch_property_value(
                submodel_identifier=submodel_identifier,
                idshort_path=idshort_path,
                value=value,
            )

            self.last_sent_values[name] = value
            updated.append(name)

        return updated