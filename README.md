# ProyectoEmbolsadora — Historian

Resumen rápido
- Servicio `historian` que lee tags definidos en `src/historian/tags.yaml`, consulta un cliente Modbus (o un mock) y escribe puntos en InfluxDB con timestamp preciso.

Lógica principal
- `tags.yaml` define una lista de tags; cada tag incluye: `name`, `type` (`Bool`, `Int16`, `Float32`), `address` (registro o bobina) y opciones como `word_byteorder` para `Float32`.
- El `historian` itera los tags, usa el cliente Modbus (real o `mock` cuando `MODBUS_HOST=mock`) y parsea el resultado con los parsers en `src/historian/parsers.py`.
- Cada tag se escribe en InfluxDB con su propio campo (clave = nombre del tag) para evitar conflictos de tipo.

Cómo ejecutar localmente
Requisitos:
- Python 3.11
- Dependencias: `pip install -r requirements.txt`

Ejecutar tests unitarios (rápido):
```powershell
python run_tests.py
```

Ejecutar el historian contra el `mock` (útil para pruebas locales):
```powershell
# exporta variables de entorno en PowerShell
$env:MODBUS_HOST = 'mock'
$env:INFLUX_URL = 'http://localhost:8086'
$env:INFLUX_TOKEN = 'ci-token'
$env:INFLUX_ORG = 'ci-org'
$env:INFLUX_BUCKET = 'ci-bucket'
python -m src.historian.main
```

Formato y cambio de tags
- El fichero de tags está en `src/historian/tags.yaml`.
- Ejemplo de tag:
```yaml
- name: filled_weight
  type: Float32
  address: 20
  word_byteorder: big
```
- Para añadir un tag nuevo: crea una entrada similar en `tags.yaml` con el `type` correcto. Los tipos soportados actualmente son `Bool`, `Int16`, `Float32`.
- Si usas `Float32`, ajusta `word_byteorder` (big/little) según cómo la PLC entregue los dos registros de 16 bits.

Docker y CI
- Hay un `Dockerfile` que produce la imagen del `historian` preparada para `linux/arm64` (target Raspberry Pi).
- La GitHub Actions CI (archivo `.github/workflows/ci.yml`) hace:
  - tests unitarios
  - setup QEMU + buildx
  - build multi-arch (linux/arm64) y guarda la imagen como artifact
  - integration: carga la imagen, arranca InfluxDB en una red Docker y ejecuta el `historian` (usando el `mock`) y valida valores en Influx.

Publicar la imagen (qué es y cómo hacerlo)
- Qué es: "publicar la imagen" significa subir la imagen Docker resultante a un registro remoto (por ejemplo GitHub Container Registry — GHCR) para que puedas desplegarla directamente en Raspberry Pi u otros hosts sin reconstruir localmente.
- Opciones comunes:
  - GHCR (recommended for GitHub projects)
  - Docker Hub

- Pasos generales para publicar manualmente a GHCR:
  1. Construir la imagen para la plataforma objetivo (ARM64):
     ```powershell
     docker buildx create --use --name mybuilder
     docker buildx build --platform linux/arm64 -t ghcr.io/<OWNER>/<REPO>:<TAG> --push .
     ```
  2. Necesitas autenticarte: en local, `echo $GITHUB_TOKEN | docker login ghcr.io -u <OWNER> --password-stdin` o usar un PAT con permisos `write:packages`.

- Automatizar con GitHub Actions: en el workflow puedes añadir un paso que haga `docker buildx build --platform linux/arm64 -t ghcr.io/${{ github.repository_owner }}/${{ github.repository }}:latest --push .`.
  - Usa el `GITHUB_TOKEN` o un secret `CR_PAT` con permisos para publicar. En repositorios públicos, también asegúrate de habilitar `packages:write` si es necesario.

Consejos y troubleshooting
- Si Influx devuelve 401 en CI, suele ser un problema de token/orden de arranque; la CI actual espera a que Influx esté listo antes de escribir.
- Si Influx devuelve 422: evita escribir diferentes tipos de campo con la misma clave. El `historian` escribe cada tag bajo su propio campo (nombre del tag) para prevenirlo.

Siguientes pasos sugeridos
- Publicar la imagen automáticamente desde CI (puedo añadir el paso y los cambios de workflow si quieres).
- Añadir ejemplos de `tags.yaml` para sensores reales que uses en tu planta.

Archivo clave
- `src/historian/main.py` — lógica de lectura y escritura.
- `src/historian/parsers.py` — conversiones `Int16`/`Float32`/`Bool`.
- `src/historian/tags.yaml` — lista de tags dinámica.

Si quieres, procedo a:
- Añadir el paso de publicación en el workflow y explicarte qué secret crear (recomendado).
- O generar una guía paso-a-paso para desplegar la imagen en una Raspberry Pi.

---
Pequeño recordatorio: si quieres que configure la publicación automática, dime en qué registro la quieres (GHCR o Docker Hub) y si prefieres usar `GITHUB_TOKEN` o un PAT/secret.
