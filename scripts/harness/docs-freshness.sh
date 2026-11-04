#!/usr/bin/env bash
# docs-freshness: lista las páginas de docs/ cuyo front-matter `last_reviewed`
# tiene más de MAX_DAYS días (default 120). Imprime "ruta<TAB>fecha<TAB>días".
# El workflow semanal abre un issue por cada una.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
max=${MAX_DAYS:-120}
now=$(date -u +%s)

# epoch_of YYYY-MM-DD -> epoch UTC. GNU date (`-d`) primero, BSD/macOS
# (`-j -f`) después; falla si la fecha no es parseable por ninguna de las
# dos. Sin el fallback BSD el script reporta todas las páginas como
# vencidas cuando se corre fuera de CI.
epoch_of() {
  date -u -d "$1" +%s 2>/dev/null || date -u -j -f '%Y-%m-%d' "$1" +%s 2>/dev/null
}

git ls-files 'docs/*.md' ':!docs/_process/*' | while IFS= read -r f; do
  d=$(awk 'NR==1&&$0!="---"{exit} /^last_reviewed:/{gsub(/"/,"",$2); print $2; exit} NR>1&&/^---/{exit}' "$f")
  [ -n "$d" ] || { printf '%s\t%s\t%s\n' "$f" "sin-fecha" "-"; continue; }
  # Una fecha ilegible se reporta como tal en vez de contarse como
  # "~20700 días" (lo que hacía el `|| echo 0` anterior).
  ts=$(epoch_of "$d") || { printf '%s\t%s\t%s\n' "$f" "$d" "fecha-ilegible"; continue; }
  days=$(( (now - ts) / 86400 ))
  if [ "$days" -gt "$max" ]; then printf '%s\t%s\t%s\n' "$f" "$d" "$days"; fi
done
