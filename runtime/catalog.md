# Catálogo de variables del historian

| name | submodel | collection | property | measurement | field | unit | type | class |
|---|---|---|---|---|---|---|---|---|
| alimentacionTolva | Alarmas |  | alimentacionTolva | historian_semantic | alimentacionTolva |  | xs:boolean | alarm |
| paradaEmergencia | Alarmas |  | paradaEmergencia | historian_semantic | paradaEmergencia |  | xs:boolean | alarm |
| Tara | Operativos | Pesada | Tara | historian_semantic | Tara | kg | xs:float | runtime |
| cantidadPesadas | Operativos | Pesada | cantidadPesadas | historian_semantic | cantidadPesadas | count | xs:int | runtime |
| estado | Operativos | Pesada | estado | historian_semantic | estado |  | xs:boolean | runtime |
| fecha | Operativos | Pesada | fecha | historian_semantic | fecha | YYYYMMDD | xs:int | runtime |
| hora | Operativos | Pesada | hora | historian_semantic | hora | HHMMSS | xs:int | runtime |
| peso | Operativos | Pesada | peso | historian_semantic | peso | kg | xs:float | runtime |
| pesoBruto | Operativos | Pesada | pesoBruto | historian_semantic | pesoBruto | kg | xs:float | runtime |
| pesoNeto | Operativos | Pesada | pesoNeto | historian_semantic | pesoNeto | kg | xs:float | runtime |
| pesoTotal | Operativos | Pesada | pesoTotal | historian_semantic | pesoTotal | kg | xs:float | runtime |
| cantidadLlenadas | Operativos | Produccion | cantidadLlenadas | historian_semantic | cantidadLlenadas | count | xs:int | runtime |
| consumoElectrico | Operativos | Produccion | consumoElectrico | historian_semantic | consumoElectrico | kWh | xs:float | runtime |
| horasProduccion | Operativos | Produccion | horasProduccion | historian_semantic | horasProduccion | h | xs:float | runtime |
| tiempoCiclo | Operativos | Produccion | tiempoCiclo | historian_semantic | tiempoCiclo | s | xs:float | runtime |
| tiempoCicloActual | Operativos | Produccion | tiempoCicloActual | historian_semantic | tiempoCicloActual | s | xs:float | runtime |
| tiempoLlenado | Operativos | Produccion | tiempoLlenado | historian_semantic | tiempoLlenado | s | xs:float | runtime |
| tiempoPreparacion | Operativos | Produccion | tiempoPreparacion | historian_semantic | tiempoPreparacion | s | xs:float | runtime |