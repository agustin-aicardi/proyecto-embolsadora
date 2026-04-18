from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

AAS_NS = {"aas": "https://admin-shell.io/aas/3/0"}


class AASUpdater:
    def __init__(self, aas_xml_path: str, mapping_path: str, tags_path: str | None = None):
        self.aas_xml_path = Path(aas_xml_path)
        self.mapping_path = Path(mapping_path)
        self.tags_path = Path(tags_path) if tags_path else None

        self.tree = ET.parse(self.aas_xml_path)
        self.root = self.tree.getroot()

        with open(self.mapping_path, "r", encoding="utf-8") as f:
            mapping_doc = yaml.safe_load(f) or {}

        self.defaults = mapping_doc.get("defaults", {})
        self.mappings = mapping_doc.get("mappings", [])

        self.index = self._build_index()
        self.tag_names = self._load_tag_names() if self.tags_path else None

        self._validate_mapping_structure()
        self._validate_mapping_targets()
        self._validate_duplicate_targets()

        if self.tag_names is not None:
            self._validate_mapping_names_exist()
            self._validate_duplicate_tag_names()

        print(f"AAS index built with {len(self.index)} properties")
        print(f"AAS mapping loaded with {len(self.mappings)} entries")
        if self.tag_names is not None:
            print(f"AAS tags loaded with {len(self.tag_names)} tag names")

    def _build_index(self) -> dict[tuple[str, str | None, str], ET.Element]:
        index: dict[tuple[str, str | None, str], ET.Element] = {}

        for submodel in self.root.findall(".//aas:submodel", AAS_NS):
            submodel_idshort_el = submodel.find("aas:idShort", AAS_NS)
            if submodel_idshort_el is None or not submodel_idshort_el.text:
                continue

            submodel_idshort = submodel_idshort_el.text.strip()

            for prop in submodel.findall("aas:submodelElements/aas:property", AAS_NS):
                prop_idshort_el = prop.find("aas:idShort", AAS_NS)
                if prop_idshort_el is None or not prop_idshort_el.text:
                    continue

                key = (submodel_idshort, None, prop_idshort_el.text.strip())
                index[key] = prop

            for collection in submodel.findall(".//aas:submodelElementCollection", AAS_NS):
                collection_idshort_el = collection.find("aas:idShort", AAS_NS)
                if collection_idshort_el is None or not collection_idshort_el.text:
                    continue

                collection_idshort = collection_idshort_el.text.strip()
                value_node = collection.find("aas:value", AAS_NS)
                if value_node is None:
                    continue

                for prop in value_node.findall("aas:property", AAS_NS):
                    prop_idshort_el = prop.find("aas:idShort", AAS_NS)
                    if prop_idshort_el is None or not prop_idshort_el.text:
                        continue

                    key = (submodel_idshort, collection_idshort, prop_idshort_el.text.strip())
                    index[key] = prop

        return index

    def _load_tag_names(self) -> list[str]:
        if self.tags_path is None:
            return []

        if not self.tags_path.exists():
            raise FileNotFoundError(f"Tags file not found: {self.tags_path}")

        with open(self.tags_path, "r", encoding="utf-8") as f:
            tags_doc = yaml.safe_load(f) or {}

        tags = tags_doc.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError("The 'tags' section must be a list.")

        names: list[str] = []
        for i, tag in enumerate(tags):
            if not isinstance(tag, dict):
                raise ValueError(f"Tag entry at index {i} must be a dictionary.")
            name = tag.get("name")
            if not name:
                raise ValueError(f"Tag entry at index {i} is missing required field 'name'.")
            names.append(name)

        return names

    def _validate_mapping_structure(self) -> None:
        if not isinstance(self.mappings, list):
            raise ValueError("The 'mappings' section must be a list.")

        for i, mapping in enumerate(self.mappings):
            if not isinstance(mapping, dict):
                raise ValueError(f"Mapping entry at index {i} must be a dictionary.")

            name = mapping.get("name")
            if not name:
                raise ValueError(f"Mapping entry at index {i} is missing required field 'name'.")

            enabled = mapping.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(f"Mapping '{name}': field 'enabled' must be boolean.")

            aas = mapping.get("aas")
            if not isinstance(aas, dict):
                raise ValueError(f"Mapping '{name}': field 'aas' must be a dictionary.")

            submodel = aas.get("submodel")
            prop = aas.get("property")

            if not submodel:
                raise ValueError(f"Mapping '{name}': missing 'aas.submodel'.")
            if not prop:
                raise ValueError(f"Mapping '{name}': missing 'aas.property'.")

    def _validate_mapping_targets(self) -> None:
        missing_targets: list[str] = []

        for mapping in self.mappings:
            if not mapping.get("enabled", True):
                continue

            name = mapping["name"]
            aas = mapping["aas"]

            key = (
                aas["submodel"],
                aas.get("collection"),
                aas["property"],
            )

            if key not in self.index:
                missing_targets.append(
                    f"name='{name}' -> submodel='{aas['submodel']}', "
                    f"collection='{aas.get('collection')}', property='{aas['property']}'"
                )

        if missing_targets:
            detail = "\n".join(missing_targets)
            raise ValueError(f"The following mapping targets do not exist in the AAS XML:\n{detail}")

    def _validate_duplicate_targets(self) -> None:
        seen: dict[tuple[str, str | None, str], str] = {}
        duplicates: list[str] = []

        for mapping in self.mappings:
            if not mapping.get("enabled", True):
                continue

            name = mapping["name"]
            aas = mapping["aas"]

            key = (
                aas["submodel"],
                aas.get("collection"),
                aas["property"],
            )

            if key in seen:
                duplicates.append(
                    f"target {key} is assigned to both '{seen[key]}' and '{name}'"
                )
            else:
                seen[key] = name

        if duplicates:
            detail = "\n".join(duplicates)
            raise ValueError(f"Duplicate AAS targets found in mapping:\n{detail}")

    def _validate_mapping_names_exist(self) -> None:
        missing_names: list[str] = []

        assert self.tag_names is not None

        for mapping in self.mappings:
            if not mapping.get("enabled", True):
                continue

            name = mapping["name"]
            if name not in self.tag_names:
                missing_names.append(name)

        if missing_names:
            detail = "\n".join(sorted(missing_names))
            raise ValueError(f"The following mapping names do not exist in tags.yaml:\n{detail}")

    def _validate_duplicate_tag_names(self) -> None:
        assert self.tag_names is not None

        seen: set[str] = set()
        duplicates: set[str] = set()

        for tag_name in self.tag_names:
            if tag_name in seen:
                duplicates.add(tag_name)
            seen.add(tag_name)

        if duplicates:
            detail = "\n".join(sorted(duplicates))
            raise ValueError(f"Duplicate tag names found in tags.yaml:\n{detail}")

    def _set_property_value(self, prop: ET.Element, value: Any) -> None:
        value_el = prop.find("aas:value", AAS_NS)
        if value_el is None:
            value_el = ET.SubElement(prop, "{https://admin-shell.io/aas/3/0}value")

        if isinstance(value, bool):
            value_el.text = "true" if value else "false"
        else:
            value_el.text = str(value)

    def update_from_dict(self, values: dict[str, Any]) -> list[str]:
        updated: list[str] = []

        for mapping in self.mappings:
            if not mapping.get("enabled", True):
                continue

            name = mapping["name"]

            if name not in values:
                continue

            aas = mapping["aas"]
            key = (
                aas["submodel"],
                aas.get("collection"),
                aas["property"],
            )

            target_prop = self.index.get(key)
            if target_prop is None:
                continue

            self._set_property_value(target_prop, values[name])
            updated.append(name)

        return updated

    def save(self, output_path: str) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.tree.write(output_path, encoding="utf-8", xml_declaration=True)