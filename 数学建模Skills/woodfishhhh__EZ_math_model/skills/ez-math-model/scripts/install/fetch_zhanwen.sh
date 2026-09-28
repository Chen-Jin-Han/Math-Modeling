#!/usr/bin/env bash
# Fetch the zhanwen/MathModel reference repo (sparse) into external/zhanwen-mathmodel/.
# Failure writes .failed marker rather than throwing; pipeline falls back to internal templates.
# Existing .complete short-circuits unless --force is given.
# Existing .skip is honored permanently.

set -uo pipefail

REPO="${REPO:-https://github.com/zhanwen/MathModel.git}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
DEFAULT_DEST="$(cd -- "$SCRIPT_DIR/../../external/zhanwen-mathmodel" 2>/dev/null && pwd || true)"
DEST="${DEST:-$DEFAULT_DEST}"
FORCE=0

# Sparse paths covering everything match_thesis.py needs.
SPARSE_PATHS=(
  "国赛论文/"
  "国赛试题/"
  "美赛论文/"
  "2024年数模悉知&论文模版/"
  "2025年数模悉知&论文模版/"
  "2024年最终获奖名单/"
  "数学建模Latex模版/"
  "README.md"
)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --dest)  DEST="$2"; shift 2 ;;
    --repo)  REPO="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$DEST" ]]; then
  echo "[fetch_zhanwen] could not resolve destination directory" >&2
  exit 1
fi

mkdir -p "$DEST"

write_marker() {
  local name="$1"; shift
  local body="${1:-$(date -u +%FT%TZ)}"
  printf '%s' "$body" > "$DEST/$name"
}
remove_marker() {
  local name="$1"
  [[ -f "$DEST/$name" ]] && rm -f "$DEST/$name"
}

if [[ -f "$DEST/.skip" ]]; then
  echo "[fetch_zhanwen] .skip marker present; user opted out permanently. Aborting."
  exit 0
fi

if [[ -f "$DEST/.complete" && $FORCE -eq 0 ]]; then
  echo "[fetch_zhanwen] .complete marker present; pass --force to refresh."
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "[fetch_zhanwen] git not found on PATH" >&2
  write_marker .failed "git not found at $(date -u +%FT%TZ)"
  exit 1
fi

# Wipe non-keep entries.
KEEP=(".gitkeep" "README.md" ".skip")
STASH="$(mktemp -d)"
trap 'rm -rf "$STASH"' EXIT

shopt -s dotglob nullglob
for entry in "$DEST"/*; do
  base="$(basename -- "$entry")"
  keep=0
  for k in "${KEEP[@]}"; do [[ "$base" == "$k" ]] && keep=1 && break; done
  if [[ $keep -eq 1 ]]; then
    mv -- "$entry" "$STASH/"
  else
    rm -rf -- "$entry"
  fi
done
shopt -u dotglob nullglob

cleanup_restore() {
  for f in "$STASH"/* "$STASH"/.[!.]* "$STASH"/..?* 2>/dev/null; do
    [[ -e "$f" ]] || continue
    mv -- "$f" "$DEST/"
  done
}

(
  cd "$DEST"
  echo "[fetch_zhanwen] cloning $REPO (sparse, depth 1) ..."
  if ! git clone --depth 1 --filter=blob:none --sparse "$REPO" . ; then
    cleanup_restore
    write_marker .failed "git clone failed at $(date -u +%FT%TZ)"
    exit 1
  fi

  echo "[fetch_zhanwen] applying sparse-checkout subset ..."
  if ! git sparse-checkout init --no-cone ; then
    cleanup_restore
    write_marker .failed "sparse-checkout init failed at $(date -u +%FT%TZ)"
    exit 1
  fi

  PATTERN_FILE=".git/info/sparse-checkout"
  : > "$PATTERN_FILE"
  for p in "${SPARSE_PATHS[@]}"; do
    printf '%s\n' "$p" >> "$PATTERN_FILE"
  done

  if ! git sparse-checkout reapply ; then
    cleanup_restore
    write_marker .failed "sparse-checkout reapply failed at $(date -u +%FT%TZ)"
    exit 1
  fi
)
rc=$?

cleanup_restore

if [[ $rc -ne 0 ]]; then
  exit "$rc"
fi

# Sanity: at least one expected path must exist.
hit=0
for p in "${SPARSE_PATHS[@]}"; do
  clean="${p%/}"
  if [[ -e "$DEST/$clean" ]]; then hit=1; break; fi
done
if [[ $hit -eq 0 ]]; then
  write_marker .failed "sparse-checkout produced no expected paths at $(date -u +%FT%TZ)"
  echo "[fetch_zhanwen] upstream layout may have changed; nothing to use" >&2
  exit 1
fi

remove_marker .failed
write_marker .complete "fetched_at=$(date -u +%FT%TZ)
repo=$REPO"
echo "[fetch_zhanwen] done."
