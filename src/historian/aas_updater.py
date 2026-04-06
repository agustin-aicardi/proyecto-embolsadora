from __future__ import annotations

import yaml
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

AAS_NS = {"aas": "https://admin-shell.io/aas/3/0"}


class AASUpdater:
    def __init__(self, aas_xml_path: str, mapping_path: str):
        self.aas_xml_path = Path(aas_xml_path)
        self.mapping_path = Path(mapping_path)

        self.tree = ET.parse(self.aas_xml_path)
        self.root = self.tree.getroot()

        with open(self.mapping_path, "r", encoding="utf-8") as f:
            mapping_doc = yaml.safe_load(f)

        self.mappings = mapping_doc.get("mappings", [])
        self.index = self._build_index()
        print(f"AAS index built with {len(self.index)} properties")

    def _build_index(self) -> dict[tuple[str, str | None, str], ET.Element]:
        index: dict[tuple[str, str | None, str], ET.Element] = {}

        for submodel in self.root.findall(".//aas:submodel", AAS_NS):
            submodel_idshort_el = submodel.find("aas:idShort", AAS_NS)
            if submodel_idshort_el is None or not submodel_idshort_el.text:
                continue

            submodel_idshort = submodel_idshort_el.text

            # properties directas del submodel
            for prop in submodel.findall("aas:submodelElements/aas:property", AAS_NS):
                prop_idshort_el = prop.find("aas:idShort", AAS_NS)
                if prop_idshort_el is None or not prop_idshort_el.text:
                    continue

                key = (submodel_idshort, None, prop_idshort_el.text)
                index[key] = prop

            # properties dentro de colecciones
            for collection in submodel.findall(".//aas:submodelElementCollection", AAS_NS):
                collection_idshort_el = collection.find("aas:idShort", AAS_NS)
                if collection_idshort_el is None or not collection_idshort_el.text:
                    continue

                collection_idshort = collection_idshort_el.text
                value_node = collection.find("aas:value", AAS_NS)
                if value_node is None:
                    continue

                for prop in value_node.findall("aas:property", AAS_NS):
                    prop_idshort_el = prop.find("aas:idShort", AAS_NS)
                    if prop_idshort_el is None or not prop_idshort_el.text:
                        continue

                    key = (submodel_idshort, collection_idshort, prop_idshort_el.text)
                    index[key] = prop

        return index

    def _set_property_value(self, prop: ET.Element, value: Any):
        value_el = prop.find("aas:value", AAS_NS)
        if value_el is None:
            value_el = ET.SubElement(prop, "{https://admin-shell.io/aas/3/0}value")

        value_el.text = str(value)

    def update_from_dict(self, values: dict[str, Any]) -> list[str]:
        updated = []

        for m in self.mappings:
            tag_name = m["tag"]

            if tag_name not in values:
                continue

            key = (
                m["submodel"],
                m.get("collection"),
                m["property"],
            )

            target_prop = self.index.get(key)
            if target_prop is None:
                continue

            self._set_property_value(target_prop, values[tag_name])
            updated.append(tag_name)

        return updated

    def save(self, output_path: str):
        self.tree.write(output_path, encoding="utf-8", xml_declaration=True)