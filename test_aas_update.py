from src.historian.aas_updater import AASUpdater

values = {
    "filled_weight": 8.7,
    "pack_count": 125,
    "cycle_count": 980,
    "conveyor_running": 1,
    "pressure": 1.18,
    "temperature": 26.5,
    "emergency_stop": 0,
}

updater = AASUpdater(
    aas_xml_path="Embolsadora_V3.xml",
    mapping_path="src/historian/aas_mapping.yaml",
)

updated = updater.update_from_dict(values)
print("Updated tags:", updated)

updater.save("Embolsadora_V3_updated.xml")
print("Saved updated AAS to Embolsadora_V3_updated.xml")