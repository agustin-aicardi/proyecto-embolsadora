#!/usr/bin/env bash
# harness-layout: verifica el layout canónico, las prohibiciones y el front-matter
# del harness documental (spec "Harness documental de repositorio", §3, §9 y §10).
#
# Idéntico en los cuatro repos de componente. Parámetros por variable de entorno:
#   HARNESS_EXPOSES_HTTP=1   exige docs/openapi.yaml (poner 0 si el repo no expone HTTP)
#
# Prohibición 9 (copias de contratos de otro repo) no se puede verificar de forma
# automática: se revisa en el PR.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
fail=0
err() { echo "::error::$*"; fail=1; }

tracked() { git ls-files -- "$@"; }

# --- 1. Archivos obligatorios -------------------------------------------------
required=(README.md AGENTS.md CLAUDE.md .env.example
  docs/architecture.md docs/development.md docs/operations.md docs/adr/index.md
  specs/README.md)
if [ "${HARNESS_EXPOSES_HTTP:-1}" = "1" ]; then required+=(docs/openapi.yaml); fi
for f in "${required[@]}"; do
  [ -f "$f" ] || err "falta el archivo obligatorio: $f"
done
if [ -f CLAUDE.md ] && ! grep -q '@AGENTS.md' CLAUDE.md; then
  err "CLAUDE.md debe ser un adaptador que incluya AGENTS.md (@AGENTS.md)"
fi
if [ -f AGENTS.md ] && ! grep -q '^## Specs' AGENTS.md; then
  err "AGENTS.md debe incluir la sección '## Specs'"
fi

# --- 2. Prohibiciones (§9) ----------------------------------------------------
# 1. .env trackeado
while IFS= read -r f; do
  case "$f" in *.example|*.sample|*.template) ;; *) err "prohibido 1: .env trackeado: $f" ;; esac
done < <(tracked '.env' '**/.env' '.env.*' '**/.env.*')
# 2. binarios compilados
while IFS= read -r f; do err "prohibido 2: binario compilado trackeado: $f"; done \
  < <(tracked '*.exe' '*.dll' '*.so' '*.dylib' '*.o' '*.a' 'bin/*')
# 3. logs de build
while IFS= read -r f; do err "prohibido 3: log trackeado: $f"; done < <(tracked '*.log')
# 4. markdown suelto en la raíz fuera de los cinco permitidos
while IFS= read -r f; do
  case "$f" in README.md|AGENTS.md|CLAUDE.md|CHANGELOG.md|LICENSE|LICENSE.md) ;; *)
    err "prohibido 4: markdown suelto en la raíz: $f (va dentro de docs/)" ;; esac
done < <(git ls-files | grep -E '^[^/]+\.md$' || true)
# 5. .specify/specs y docs/superpowers
if [ -n "$(tracked '.specify/specs/*')" ]; then err "prohibido 5: .specify/specs/ duplica specs/"; fi
if [ -n "$(tracked 'docs/superpowers/*')" ]; then err "docs/superpowers/ no debe existir: los diseños van a specs/NNN-slug/"; fi
# 6. artefactos speckit en repos sin specs de speckit
has_speckit_specs=0
for s in specs/*/spec.md; do
  [ -f "$s" ] && grep -q '^origin: speckit' "$s" && has_speckit_specs=1
done
if [ "$has_speckit_specs" = 0 ] && [ -n "$(tracked '.github/agents/speckit.*' '.github/prompts/speckit.*')" ]; then
  err "prohibido 6: .github/agents|prompts/speckit.* en un repo sin specs de speckit"
fi
# 8. vistas de sistema dentro del repo de componente
while IFS= read -r f; do
  case "$f" in docs/_process/pendiente-migrar-al-hub/*) ;; *)
    err "prohibido 8: vista de sistema en un repo de componente (va al hub): $f" ;; esac
done < <(git ls-files | grep -E '(^|/)00-context\.md$|^docs/(system|c4)/' || true)

# --- 2b. Contrato §10.0: secciones, veredicto y marcas de procedencia ---------
# Lo que §10.0 pide y el layout por sí solo no alcanza a ver: que las páginas
# que el harness unifica tengan las secciones acordadas, en el orden acordado,
# y que las marcas que hacen auditable una spec (veredicto, divergencia,
# origen de cada RF) estén puestas.

# Las seis secciones del README, en orden (§3.1).
README_SECTIONS=("Qué es y dónde corre" "Quickstart" "Arquitectura" "Contratos"
  "Operación" "Estado y enlaces")
# Las seis secciones de toda spec, en orden (.specify/templates/spec-template.md).
SPEC_SECTIONS=("Contexto y problema" "Alcance" "Requisitos" "Criterios de éxito"
  "Decisiones" "Riesgos y preguntas abiertas")

# check_sections FILE LABEL SECCIÓN...
# Exige que estén todas y en ese orden RELATIVO. Las secciones extra se
# permiten e incluso se intercalan a propósito (`## Modelo de datos` en la 001,
# `## Divergencias con la especificación original` en la 002), así que esto
# verifica una subsecuencia, no una igualdad.
check_sections() {
  local file=$1 label=$2; shift 2
  [ -f "$file" ] || return 0
  local headings prev=0 pos want
  # `|| true` también acá: un archivo sin NINGÚN `## ` hace que este grep
  # devuelva 1 y, con pipefail, el script se muere sin imprimir una línea —
  # CI queda en rojo con el log vacío y los chequeos siguientes no corren.
  headings=$(grep -E '^##[[:space:]]' "$file" \
    | sed -E 's/^##[[:space:]]+//; s/[[:space:]]+$//' || true)
  for want in "$@"; do
    # `|| true`: con `pipefail`, el grep que no matchea —justo el caso que
    # hay que reportar— haría abortar el script sin imprimir nada.
    pos=$(printf '%s\n' "$headings" | grep -nxF -- "$want" | head -1 | cut -d: -f1 || true)
    if [ -z "$pos" ]; then
      err "$label: $file no tiene la sección '## $want'"
    elif [ "$pos" -lt "$prev" ]; then
      err "$label: $file tiene '## $want' fuera de orden (§10.0 fija el orden de las secciones)"
    else
      prev=$pos
    fi
  done
}

# fm_value FILE KEY -> el valor del front-matter, vacío si falta o está en blanco.
fm_value() {
  awk -v k="$2" '
    { sub(/\r$/, "") }
    NR==1 { if ($0 != "---") exit; next }
    /^---[ \t]*$/ { exit }
    {
      pos = index($0, ":")
      if (pos > 0) {
        key = substr($0, 1, pos - 1); val = substr($0, pos + 1)
        gsub(/^[ \t]+|[ \t]+$/, "", key)
        gsub(/^[ \t]+|[ \t]+$/, "", val)
        # Un comentario YAML no es un valor. Sin esto, una clave que la
        # plantilla trae comentada (`divergencia:   # ref a la bitácora…`)
        # cuenta como valor puesto: deja pasar justo lo que hay que frenar, y
        # exime de §4.7 (clave presente y vacía = faltante) a toda clave con
        # comentario. Un valor entrecomillado se respeta tal cual, porque su
        # `#` es parte del valor (`"…/bitacora-de-alcance-edge.md#edge-002"`).
        if (val ~ /^"/) { sub(/^"/, "", val); sub(/".*$/, "", val) }
        else {
          sub(/[ \t]+#.*$/, "", val)
          sub(/^#.*$/, "", val)
          gsub(/[ \t]+$/, "", val)
        }
        if (key == k) { print val; exit }
      }
    }' "$1"
}

# check_verdict SPEC
# El `veredicto` es el resultado de reconciliar la spec con el código, así que
# va de la mano de `reconciliado`: una spec nueva todavía no tiene ninguno de
# los dos, y una reconciliada tiene los dos. Si hay veredicto tiene que ser
# A, B o C; y un veredicto B o C —o un status `superseded`— significa que la
# spec no describe lo implementado, así que tiene que apuntar a la bitácora
# de alcance por `divergencia`.
check_verdict() {
  local spec=$1
  local ver rec st div st_needs_div
  ver=$(fm_value "$spec" veredicto); rec=$(fm_value "$spec" reconciliado)
  st=$(fm_value "$spec" status);     div=$(fm_value "$spec" divergencia)
  if [ -n "$ver" ] && [ -z "$rec" ]; then
    err "$spec: tiene veredicto ($ver) pero no la fecha 'reconciliado'"
  fi
  if [ -z "$ver" ] && [ -n "$rec" ]; then
    err "$spec: tiene 'reconciliado: $rec' pero no veredicto"
  fi
  # Los cinco de §6.1, como los documenta specs/README.md: A implementado como
  # se especificó, B implementado distinto, C descartado, D todavía querido,
  # E basura. Con solo A/B/C el gate rechazaba una spec D bien escrita —y este
  # repo ya tiene pendientes con veredicto D en su índice.
  case "$ver" in
    ""|A|B|C|D|E) ;;
    *) err "$spec: veredicto inválido: '$ver' (los válidos son A, B, C, D y E)" ;;
  esac
  # `divergencia` obligatoria en la unión de los dos criterios: el veredicto
  # B/C de §6.1 y los status que la plantilla ya exigía (partial, abandoned,
  # superseded). Pedir solo B/C/superseded habría angostado en silencio una
  # regla que ya estaba escrita.
  case "$st" in partial|abandoned|superseded) st_needs_div=1 ;; *) st_needs_div=0 ;; esac
  if [ -z "$div" ] && { [ "$ver" = B ] || [ "$ver" = C ] || [ "$st_needs_div" = 1 ]; }; then
    err "$spec: veredicto '$ver' / status '$st' exige 'divergencia' (ref a la bitácora de alcance)"
  fi
}

# check_rf_origin SPEC
# Todo RF-NNN lleva su marca de procedencia: `origen: original` (lo decidió esta
# spec) o `origen: derivado` (se dedujo del código al reconciliar). Sin la marca
# no se puede saber si un requisito es una decisión o una observación.
check_rf_origin() {
  local spec=$1 bad
  # `|| true`: el caso bueno es que `grep -v` no matchee nada, y con
  # `pipefail` eso devuelve 1 y aborta el script en silencio.
  bad=$(grep -nE '\*\*RF-[0-9]{3}[a-z]?\*\*' "$spec" \
    | grep -vE 'origen:[[:space:]]*(original|derivado)' | cut -d: -f1 | tr '\n' ' ' || true)
  [ -z "$bad" ] || err "$spec: RF sin 'origen: original|derivado' en las líneas: $bad"
}

check_sections README.md README "${README_SECTIONS[@]}"

# --- 3. Front-matter ----------------------------------------------------------
# Claves que pueden estar presentes y vacías por diseño (un ADR que no
# reemplaza ni es reemplazado deja `supersedes:`/`superseded_by:` en blanco).
# Para el resto de las claves requeridas se exige también un valor: sin esto
# un `last_reviewed:` vacío pasaba el gate y después docs-freshness.sh abría
# un issue por esa misma página.
FM_BLANK_OK="supersedes superseded_by"

# missing_keys FILE KEY...  -> imprime las claves que faltan y las que están
# presentes pero vacías (como `clave(vacía)`).
missing_keys() {
  local file=$1; shift
  awk -v keys="$*" -v blankok="$FM_BLANK_OK" '
    { sub(/\r$/, "") }
    NR==1 { if ($0 != "---") { print "front-matter"; exit } next }
    /^---[ \t]*$/ { closed=1; exit }
    {
      pos = index($0, ":")
      if (pos > 0) {
        key = substr($0, 1, pos - 1)
        val = substr($0, pos + 1)
        gsub(/^[ \t]+|[ \t]+$/, "", key)
        gsub(/^[ \t]+|[ \t]+$/, "", val)
        # Un comentario YAML no es un valor. Sin esto, una clave que la
        # plantilla trae comentada (`divergencia:   # ref a la bitácora…`)
        # cuenta como valor puesto: deja pasar justo lo que hay que frenar, y
        # exime de §4.7 (clave presente y vacía = faltante) a toda clave con
        # comentario. Un valor entrecomillado se respeta tal cual, porque su
        # `#` es parte del valor (`"…/bitacora-de-alcance-edge.md#edge-002"`).
        if (val ~ /^"/) { sub(/^"/, "", val); sub(/".*$/, "", val) }
        else {
          sub(/[ \t]+#.*$/, "", val)
          sub(/^#.*$/, "", val)
          gsub(/[ \t]+$/, "", val)
        }
        seen[key] = 1
        if (val != "") hasval[key] = 1
      }
    }
    END {
      if (!closed) { print "front-matter(sin cierre)"; exit }
      split(blankok, b, " ")
      for (i in b) ok[b[i]] = 1
      n = split(keys, k, " ")
      for (i = 1; i <= n; i++) {
        if (!(k[i] in seen)) { print k[i]; continue }
        if (!(k[i] in hasval) && !(k[i] in ok)) print k[i] "(vacía)"
      }
    }' "$file"
}
check_fm() {
  local file=$1; shift
  local m; m=$(missing_keys "$file" "$@" | tr '\n' ' ')
  [ -z "$m" ] || err "front-matter incompleto en $file (falta: $m)"
}
# 7. todo .md bajo docs/ lleva title, owner y last_reviewed (los ADR, además, id/status/date)
while IFS= read -r f; do
  case "$f" in
    docs/adr/EDGE-ADR-*|docs/adr/*-ADR-*) check_fm "$f" id title status date deciders supersedes superseded_by owner last_reviewed ;;
    *) check_fm "$f" title owner last_reviewed ;;
  esac
done < <(git ls-files 'docs/*.md')
# specs/README.md
[ -f specs/README.md ] && check_fm specs/README.md title owner last_reviewed
# toda spec: front-matter completo, al menos un RF-NNN, listada en specs/README.md
for d in specs/*/; do
  d=${d%/}; n=$(basename "$d")
  [ -f "$d/spec.md" ] || { err "$d no tiene spec.md"; continue; }
  check_fm "$d/spec.md" id title tier status owner date repos origin
  grep -qE '\*\*RF-[0-9]{3}[a-z]?\*\*' "$d/spec.md" || err "$d/spec.md no tiene ningún RF-NNN"
  [ -f "$d/plan.md" ] && check_fm "$d/plan.md" id spec status
  grep -q "$n" specs/README.md || err "specs/README.md no lista la spec $n"
  # Satélites absorbidos (§6.4): el cuerpo de estos archivos vive dentro de
  # spec.md y plan.md. `research.md` y `contracts/` NO son satélites: se quedan.
  [ -f "$d/tasks.md" ] && err "$d/tasks.md: las tareas viven en plan.md"
  [ -f "$d/quickstart.md" ] && err "$d/quickstart.md: el quickstart se absorbe en plan.md"
  [ -f "$d/data-model.md" ] && err "$d/data-model.md: el modelo de datos se absorbe en spec.md"
  [ -d "$d/checklists" ] && err "$d/checklists/: los criterios de éxito se absorben en spec.md"
  check_sections "$d/spec.md" spec "${SPEC_SECTIONS[@]}"
  check_verdict "$d/spec.md"
  check_rf_origin "$d/spec.md"
  if [ -f "$d/plan.md" ]; then
    grep -qE '\bT-[0-9]{3}\b' "$d/plan.md" || err "$d/plan.md no tiene ninguna tarea T-NNN"
  fi
done

if [ "$fail" -ne 0 ]; then echo "harness-layout: FALLÓ"; exit 1; fi
echo "harness-layout: OK"
