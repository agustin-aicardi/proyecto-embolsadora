from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_catalog(mapping_doc: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = mapping_doc.get("defaults", {})
    default_historian = defaults.get("historian", {})
    mappings = mapping_doc.get("mappings", [])

    catalog: list[dict[str, Any]] = []

    for entry in mappings:
        if not entry.get("enabled", True):
            continue

        name = entry["name"]
        aas = entry.get("aas", {})
        historian = entry.get("historian", {})
        data = entry.get("data", {})
        semantics = entry.get("semantics", {})

        measurement = historian.get(
            "measurement",
            default_historian.get("measurement", "historian_semantic"),
        )

        tags = historian.get("tags", {})

        catalog_entry = {
            "name": name,
            "aas_submodel": aas.get("submodel"),
            "aas_collection": aas.get("collection"),
            "aas_property": aas.get("property"),
            "influx_measurement": measurement,
            "influx_field": name,
            "influx_tags": tags,
            "value_type": data.get("value_type"),
            "unit": data.get("unit"),
            "default": data.get("default"),
            "description": semantics.get("description"),
            "class": semantics.get("class"),
        }

        catalog.append(catalog_entry)

    catalog.sort(
        key=lambda x: (
            x.get("aas_submodel") or "",
            x.get("aas_collection") or "",
            x.get("aas_property") or "",
        )
    )
    return catalog


def write_json(catalog: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def write_markdown(catalog: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Catálogo de variables del historian")
    lines.append("")
    lines.append(
        "| name | submodel | collection | property | measurement | field | unit | type | class |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|"
    )

    for item in catalog:
        lines.append(
            f"| {item['name']} | "
            f"{item.get('aas_submodel', '') or ''} | "
            f"{item.get('aas_collection', '') or ''} | "
            f"{item.get('aas_property', '') or ''} | "
            f"{item.get('influx_measurement', '') or ''} | "
            f"{item.get('influx_field', '') or ''} | "
            f"{item.get('unit', '') or ''} | "
            f"{item.get('value_type', '') or ''} | "
            f"{item.get('class', '') or ''} |"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    mapping_path = Path(__file__).parent / "aas_mapping.yaml"
    json_output = Path("runtime/catalog.json")
    md_output = Path("runtime/catalog.md")

    mapping_doc = load_mapping(mapping_path)
    catalog = build_catalog(mapping_doc)

    write_json(catalog, json_output)
    write_markdown(catalog, md_output)

    print(f"Catalog generated:")
    print(f" - {json_output}")
    print(f" - {md_output}")
    print(f"Entries: {len(catalog)}")


if __name__ == "__main__":
    main()