#!/usr/bin/env bash
# Tests de `check-layout.sh`. El verificador del harness es el único gate del
# contrato documental, así que un bug suyo no se ve: pasa en verde y deja pasar
# lo que tenía que frenar. Este script lo ejercita en negativo.
#
# Cada caso corre sobre una copia descartable del repo (un git init con los
# archivos trackeados), le aplica una mutación y verifica que el verificador
# falle —con el mensaje correcto— o que siga pasando, según el caso.
#
# Uso: bash scripts/harness/test-check-layout.sh
set -uo pipefail

REPO=$(git rev-parse --show-toplevel)
SCRIPT=$REPO/scripts/harness/check-layout.sh
TMP=$(mktemp -d)
PRISTINE=$TMP/pristine
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }

# Sandbox base: los archivos trackeados del repo en un git propio.
mkdir -p "$PRISTINE"
# Desde el índice (no desde HEAD): así corre también con cambios staged sin commitear.
# En CI el índice es igual a HEAD, así que da lo mismo.
(cd "$REPO" && git ls-files -z | tar --null -T - -cf -) | tar -x -C "$PRISTINE"
git -C "$PRISTINE" init -q
git -C "$PRISTINE" add -A
git -C "$PRISTINE" -c user.email=t@t -c user.name=t commit -qm base

# run_case DESCRIPCIÓN EXPECTATIVA PATRÓN -- la mutación llega por stdin y se
# ejecuta con $S apuntando a la copia. EXPECTATIVA es `fail` o `pass`.
run_case() {
  local desc=$1 expect=$2 pattern=${3:-}
  local S=$TMP/case; rm -rf "$S"; cp -R "$PRISTINE" "$S"
  ( cd "$S" && eval "$(cat)" && git add -A >/dev/null 2>&1 )
  local out rc
  out=$(cd "$S" && HARNESS_EXPOSES_HTTP=0 bash "$SCRIPT" 2>&1); rc=$?

  if [ "$expect" = pass ]; then
    if [ "$rc" -eq 0 ]; then green "  ok   $desc"; pass=$((pass+1));
    else red "  FAIL $desc — esperaba exit 0, dio $rc:"; printf '%s\n' "$out" | sed 's/^/         /'; fail=$((fail+1)); fi
    return
  fi
  # expect fail: no alcanza con que salga 1 — tiene que DECIR qué pasó.
  if [ "$rc" -eq 0 ]; then
    red "  FAIL $desc — esperaba que fallara y pasó (exit 0)"; fail=$((fail+1)); return
  fi
  if [ -z "$(printf '%s' "$out" | tr -d '[:space:]')" ]; then
    red "  FAIL $desc — falló (exit $rc) pero SIN NINGÚN MENSAJE (set -e silencioso)"; fail=$((fail+1)); return
  fi
  if [ -n "$pattern" ] && ! printf '%s\n' "$out" | grep -qF -- "$pattern"; then
    red "  FAIL $desc — falló pero sin el mensaje esperado ('$pattern'):"
    printf '%s\n' "$out" | sed 's/^/         /'; fail=$((fail+1)); return
  fi
  green "  ok   $desc"; pass=$((pass+1))
}

echo "== caso base =="
run_case "repo sin mutar pasa" pass <<<'true'

echo "== secciones del README y de spec.md =="
run_case "README sin una de las seis secciones" fail "no tiene la sección '## Contratos'" \
  <<<"sed -i.bak 's|^## Contratos\$|## Contratos y demas|' README.md && rm -f README.md.bak"
run_case "README con las secciones fuera de orden" fail "fuera de orden" <<'EOC'
python3 - <<'PY'
import pathlib
p = pathlib.Path("README.md"); s = p.read_text()
s = s.replace("## Quickstart", "## TMP").replace("## Arquitectura", "## Quickstart").replace("## TMP", "## Arquitectura")
p.write_text(s)
PY
EOC
run_case "spec sin una de las seis secciones" fail "no tiene la sección '## Alcance'" \
  <<<"sed -i.bak 's|^## Alcance\$|## Scope|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
# Hallazgo #1 del review: un archivo sin NINGÚN `## ` hacía que el grep de
# check_sections devolviera 1 y, con pipefail, matara el script sin imprimir nada.
run_case "README sin ningún heading '## ' reporta en vez de morir mudo" fail "no tiene la sección" \
  <<<"printf '%s\n' '# Titulo' '' 'Cuerpo sin secciones.' > README.md"
run_case "spec sin ningún heading '## ' reporta en vez de morir mudo" fail "no tiene la sección" <<'EOC'
python3 - <<'PY'
import pathlib
p = pathlib.Path("specs/001-historian-semantico/spec.md"); s = p.read_text()
fm = s.split("---")[1]
p.write_text("---" + fm + "---\n\n# 001 — x\n\n**RF-001** `origen: original` — x.\n")
PY
EOC

echo "== veredicto, reconciliado y divergencia =="
run_case "veredicto inválido" fail "veredicto inválido" \
  <<<"sed -i.bak 's|^veredicto: A\$|veredicto: Z|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
# Hallazgo #2: §6.1 define cinco veredictos (A..E), no tres.
run_case "veredicto D es válido (specs/README.md lo documenta)" pass \
  <<<"sed -i.bak 's|^veredicto: A\$|veredicto: D|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
run_case "veredicto E es válido" pass \
  <<<"sed -i.bak 's|^veredicto: A\$|veredicto: E|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
run_case "veredicto B sin divergencia" fail "exige 'divergencia'" \
  <<<"sed -i.bak 's|^veredicto: A\$|veredicto: B|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
# Hallazgo #3: fm_value no sacaba el comentario YAML, así que una `divergencia:`
# dejada como la trae la plantilla (con su `# …`) contaba como valor puesto.
run_case "veredicto B con divergencia solo comentada (como la plantilla)" fail "exige 'divergencia'" \
  <<<"sed -i.bak -e 's|^veredicto: A\$|veredicto: B|' -e 's|^divergencia:.*|divergencia:                    # ref a la bitacora de alcance|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
run_case "veredicto con valor y comentario al lado es válido" pass \
  <<<"sed -i.bak 's|^veredicto: A\$|veredicto: A    # A \| B \| C \| D \| E|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
run_case "veredicto sin reconciliado" fail "no la fecha 'reconciliado'" \
  <<<"sed -i.bak 's|^reconciliado: .*|reconciliado:|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"
# Hallazgo #6: la plantilla pedía divergencia para partial y abandoned también.
run_case "status abandoned sin divergencia" fail "exige 'divergencia'" \
  <<<"sed -i.bak 's|^status: done\$|status: abandoned|' specs/001-historian-semantico/spec.md && rm -f specs/001-historian-semantico/spec.md.bak"

echo "== front-matter con comentarios (§4.7) =="
# Hallazgo #3, tercera consecuencia: una clave cuyo único contenido es un
# comentario está vacía, y §4.7 dice que una clave vacía cuenta como faltante.
run_case "last_reviewed solo con comentario cuenta como vacía" fail "last_reviewed" \
  <<<"sed -i.bak 's|^last_reviewed: .*|last_reviewed:                 # AAAA-MM-DD|' docs/development.md && rm -f docs/development.md.bak"

echo "== marcas de procedencia, tareas y satélites =="
run_case "RF sin marca de origen" fail "RF sin 'origen" <<'EOC'
python3 - <<'PY'
import pathlib
p = pathlib.Path("specs/001-historian-semantico/spec.md"); s = p.read_text()
p.write_text(s.replace("**RF-001** `origen: derivado` —", "**RF-001** —", 1))
PY
EOC
run_case "plan.md sin ninguna tarea T-NNN" fail "no tiene ninguna tarea T-NNN" \
  <<<"printf '%s\n' '---' 'id: \"001\"' 'spec: ./spec.md' 'status: done' '---' '' '# 001 — plan sin tareas' > specs/001-historian-semantico/plan.md"
run_case "satélite sin absorber (quickstart.md)" fail "el quickstart se absorbe en plan.md" \
  <<<"echo '# q' > specs/001-historian-semantico/quickstart.md"
run_case "satélite sin absorber (data-model.md)" fail "el modelo de datos se absorbe en spec.md" \
  <<<"echo '# d' > specs/001-historian-semantico/data-model.md"
run_case "satélite sin absorber (checklists/)" fail "los criterios de éxito se absorben" \
  <<<"mkdir -p specs/001-historian-semantico/checklists && echo '# c' > specs/001-historian-semantico/checklists/requirements.md"

echo
if [ "$fail" -ne 0 ]; then red "test-check-layout: $pass ok, $fail FALLARON"; exit 1; fi
green "test-check-layout: $pass ok, 0 fallaron"
