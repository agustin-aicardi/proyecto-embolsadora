from src.historian.aas_updater import AASUpdater

values = {
    "peso_actual": 30.4,
    "cantidad_pesadas": 125,
    "estado_pesada": True,
    "tiempo_ciclo_actual": 2.35,
    "consumo_electrico": 1.18,
    "cantidad_llenadas": 980,
    "parada_emergencia": False,
}

updater = AASUpdater(
    aas_xml_path="Embolsadora_V3.xml",
    mapping_path="src/historian/aas_mapping.yaml",
    tags_path="src/historian/tags.yaml",
)

updated = updater.update_from_dict(values)
print("Updated tags:", updated)

updater.save("Embolsadora_V3_updated.xml")
print("Saved updated AAS to Embolsadora_V3_updated.xml")