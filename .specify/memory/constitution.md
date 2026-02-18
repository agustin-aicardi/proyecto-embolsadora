# ProyectoEmbolsadora Constitution

## Core Principles

### I. Spec-Driven Development (NON-NEGOTIABLE)
Toda funcionalidad debe seguir el ciclo: Specification (Qué/Por qué) → Plan (Cómo/Arquitectura) → Tasks (Desglose) → Implementation. No se debe generar código sin un plan técnico aprobado que valide las dependencias.

### II. Industrial Protocol Standards (Modbus)
Se debe utilizar exclusivamente **Pymodbus v3.1.0** o superior. Queda estrictamente prohibido el uso de APIs obsoletas (ej. `pymodbus.client.sync` o el antiguo `ModbusSlaveContext`). Todas las lecturas deben manejar el orden de bytes (Endianness) para tipos de datos de 32 bits (Floats/Int32).

### III. Docker-First Infrastructure
El sistema debe ser orquestado mediante Docker Compose. La comunicación entre el Historian, el Simulador de PLC y la Base de Datos debe realizarse mediante **nombres de servicio** (DNS interno de Docker) y nunca mediante direcciones IP estáticas o `localhost`.

### IV. Hardware Target: Raspberry Pi (ARM64)
Todo desarrollo debe ser compatible con la arquitectura ARM64. Se deben utilizar imágenes base "slim" (ej. `python:3.11-slim-bookworm`) para optimizar el almacenamiento y el rendimiento en la Raspberry Pi.

### V. Resilience & Observability
Cualquier operación de red (Modbus TCP o escritura en InfluxDB) debe implementar una política de reintentos (retry logic) con un intervalo de 5 segundos. El sistema debe producir logs estructurados para facilitar el debug remoto vía SSH.

## Technical Constraints

### Technology Stack
- **Runtime**: Python 3.11+
- **Database**: InfluxDB 2.x (usando `influxdb-client`)
- **Modbus**: Pymodbus v3+
- **Orchestration**: Docker Compose V2

### Data Handling
- El mapeo de tags debe ser dinámico (vía archivo YAML/JSON).
- Soporte obligatorio para tipos: Boolean, Int16, Int32, y Float32 (utilizando 2 registros de 16 bits).

## Development Workflow

### Planning Phase
El `plan.md` debe validar explícitamente la red de Docker y las versiones de las librerías antes de proceder a la implementación de tareas.

### Implementation Phase
El agente de IA debe verificar que cada tarea de código cumpla con los principios de esta Constitución, especialmente la compatibilidad con Pymodbus v3.

## Governance
Esta Constitución es la autoridad máxima del proyecto. Cualquier cambio en la arquitectura o stack tecnológico requiere una enmienda en este documento antes de ser ejecutada.

**Version**: 1.0.0 | **Ratified**: 2026-02-16 | **Last Amended**: 2026-02-16
