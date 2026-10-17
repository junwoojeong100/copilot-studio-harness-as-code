# shellcheck shell=bash
# Helpers shared by the lab scripts. Source this file; do not execute it.

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHARED_DIR="$(cd "$LAB_DIR/../../shared" && pwd)"
SERVER_DIR="$LAB_DIR/server"
ENV_FILE="$LAB_DIR/.env.local"

log() { printf '%s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

sha256() { if command -v shasum >/dev/null 2>&1; then shasum -a 256; else sha256sum; fi | cut -d' ' -f1; }

# Build-time copy of the single source of truth (../../shared). The copies are git-ignored.
sync_shared() {
  cp "$SHARED_DIR/classify_issue.py" "$SERVER_DIR/classify_issue.py"
  cp "$SHARED_DIR/label-policy.yaml" "$SERVER_DIR/label-policy.yaml"
  log "[sync] shared/classify_issue.py + shared/label-policy.yaml -> server/"
}

# .env.local is a plain KEY=VALUE file (git-ignored, chmod 600).
env_get() {
  [[ -f "$ENV_FILE" ]] || return 0
  { grep -E "^$1=" "$ENV_FILE" || true; } | tail -n 1 | cut -d= -f2-
}

env_set() {
  local tmp="$ENV_FILE.tmp"
  (
    umask 077
    { [[ -f "$ENV_FILE" ]] && { grep -v -E "^$1=" "$ENV_FILE" || true; }; printf '%s=%s\n' "$1" "$2"; } > "$tmp"
  )
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

env_unset() {
  [[ -f "$ENV_FILE" ]] || return 0
  local tmp="$ENV_FILE.tmp"
  ( umask 077; { grep -v -E "^$1=" "$ENV_FILE" || true; } > "$tmp" )
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

# Generates the API key once; the key itself is never printed.
ensure_api_key() {
  if [[ -z "$(env_get API_KEY)" ]]; then
    command -v openssl >/dev/null 2>&1 || die "openssl is required to generate the API key"
    env_set API_KEY "$(openssl rand -hex 24)"
    log "[key] generated a new API key in .env.local (chmod 600, not printed)"
  else
    chmod 600 "$ENV_FILE"
    log "[key] using the existing API key from .env.local (not printed)"
  fi
}

# Deterministic image tag: same sources -> same tag -> the build is skipped on re-runs.
content_hash() {
  ( cd "$SERVER_DIR" && cat Dockerfile requirements.txt server.py classify_issue.py label-policy.yaml | sha256 | cut -c1-12 )
}
