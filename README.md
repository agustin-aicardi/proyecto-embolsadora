# Proyecto Embolsadora – IIoT Historian & Asset Administration Shell

Este proyecto implementa una arquitectura de digitalización industrial basada en **Asset Administration Shell (AAS)** y **series temporales** para el monitoreo de una máquina embolsadora.

El sistema adquiere datos desde un PLC (actualmente simulado), los almacena en una base de datos de series temporales y actualiza una representación semántica del sistema mediante AAS.

---

# Arquitectura del sistema

El sistema sigue un pipeline típico de **Industrial IoT (IIoT)**:
PLC / Mock Modbus
↓
Modbus Reader
↓
Historian Middleware (Python)
↓
InfluxDB (series temporales)
↓
Runtime AAS XML
↓
FA³ST AAS Server


El middleware cumple dos funciones principales:

- almacenamiento histórico de datos en **InfluxDB**
- actualización dinámica del **Asset Administration Shell**

Esto permite separar:

- **datos históricos** (InfluxDB)
- **estructura semántica del sistema** (AAS)

---

# Componentes del sistema

## Historian Middleware

Aplicación Python que:

- lee variables por **Modbus**
- aplica un **mapping semántico basado en AAS**
- guarda datos en **InfluxDB**
- actualiza el **AAS runtime**

Archivos principales:  
src/historian/  
├── main.py  
├── modbus_reader.py  
├── mock_modbus.py  
├── aas_updater.py  
├── aas_mapping.yaml  
├── tags.yaml  


---

## InfluxDB

Base de datos de series temporales que almacena:

- valores
- timestamp
- tags semánticos derivados del AAS

Ejemplo de tags utilizados:
aas_submodel  
aas_collection  
aas_property  

Esto permite reconstruir la jerarquía semántica del sistema directamente desde la base de datos.

---

## Asset Administration Shell

El sistema mantiene una representación AAS de la máquina.

Archivo base del modelo:
Embolsadora_V3.xml

Durante la ejecución se genera dinámicamente:
runtime/Embolsadora_runtime.xml

Este archivo refleja el estado actual de las variables del sistema.

---

# Variables del sistema

Actualmente el sistema genera variables simuladas como:

- peso
- pesoBruto
- pesoNeto
- pesoTotal
- cantidadPesadas
- cantidadLlenadas
- tiempoCiclo
- tiempoPreparacion
- tiempoLlenado
- consumoElectrico
- horasProduccion
- alimentacionTolva
- paradaEmergencia
- fecha
- hora
- Tara

Los datos son generados automáticamente mediante un **mock Modbus PLC**.

---

# Catálogo de variables

El proyecto genera automáticamente un catálogo de variables basado en el mapping AAS.

Archivos generados:
runtime/catalog.json  
runtime/catalog.md  

El catálogo describe:

- submodelo AAS
- collection
- property
- measurement en InfluxDB
- field
- unidad
- descripción

Sirve como referencia para saber **cómo consultar cada variable en la base de datos**.

---

# Ejecución del sistema

## 1. Clonar repositorio
git clone <repo>
cd ProyectoEmbolsadora


## 2. Levantar contenedores
docker compose up -d

Esto levanta:

- middleware historian
- InfluxDB
- simulación PLC

El sistema comienza a generar datos automáticamente.

---

# Acceso a InfluxDB
URL: http://localhost:8086  
ORG: org  
BUCKET: bucket  


Las consultas pueden realizarse utilizando **Flux**.

Ejemplo para obtener el último valor de peso:  
from(bucket: "bucket")  
|> range(start: -10m)  
|> filter(fn: (r) => r._measurement == "historian_semantic")  
|> filter(fn: (r) => r._field == "peso")  
|> last()  


---

# Estructura semántica

La estructura del sistema está definida en:
src/historian/aas_mapping.yaml


Este archivo define la relación entre:
AAS Submodel
→ Submodel Collection
→ Property
→ Variable historian

De esta forma los datos históricos pueden relacionarse con la estructura semántica del sistema.

---

# Estado actual del proyecto

Actualmente el sistema:

- simula un PLC mediante Mock Modbus
- almacena datos en InfluxDB
- actualiza el runtime AAS
- genera catálogo automático de variables
- utiliza tags semánticos derivados del AAS

---

# Objetivo del proyecto

Este proyecto forma parte de una **tesis de maestría en Informática Industrial**, cuyo objetivo es desarrollar una arquitectura de digitalización basada en:

- **Asset Administration Shell**
- **Industrial IoT**
- **series temporales**
- **RAMI 4.0**

La propuesta busca separar la capa de **información semántica del sistema** de la capa de **almacenamiento histórico de datos**, manteniendo una relación consistente entre ambas.

---

# Licencia

Uso académico.
