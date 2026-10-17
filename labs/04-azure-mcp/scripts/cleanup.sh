#!/usr/bin/env bash
# Deletes the lab's resource group (and everything in it). Requires --yes.
#   ./scripts/cleanup.sh          -> only lists what WOULD be deleted (exit 2)
#   ./scripts/cleanup.sh --yes    -> az group delete -y --no-wait
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-csharness-lab}"
CONFIRMED=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y) CONFIRMED=1 ;;
    -h|--help) sed -n '2,5p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $arg (see --help)" ;;
  esac
done

command -v az >/dev/null 2>&1 || die "Azure CLI (az) is required"
if ! ACCOUNT="$(az account show --query "join('|', [name, id])" -o tsv 2>/dev/null)"; then
  die "Not logged in to Azure. Run 'az login' first."
fi
IFS='|' read -r SUB_NAME SUB_ID <<<"$ACCOUNT"
log "[az] subscription: $SUB_NAME ($SUB_ID)"

if [[ "$(az group exists -n "$RESOURCE_GROUP")" != "true" ]]; then
  log "Resource group '$RESOURCE_GROUP' does not exist. Nothing to delete."
  env_unset MCP_ENDPOINT
  exit 0
fi

PURPOSE="$(az group show -n "$RESOURCE_GROUP" --query 'tags.purpose' -o tsv)"
[[ "$PURPOSE" == "copilot-studio-harness-lab" ]] \
  || die "refusing to delete '$RESOURCE_GROUP': it lacks the tag purpose=copilot-studio-harness-lab"

log "The resource group '$RESOURCE_GROUP' and ALL of the following resources will be deleted:"
az resource list -g "$RESOURCE_GROUP" -o table >&2

if [[ "$CONFIRMED" != "1" ]]; then
  log ""
  log "Nothing was deleted. Re-run with --yes to confirm:  ./scripts/cleanup.sh --yes"
  exit 2
fi

az group delete -n "$RESOURCE_GROUP" --yes --no-wait
env_unset MCP_ENDPOINT
log "Deletion started (runs in the background, takes a few minutes)."
log "Check:  az group exists -n $RESOURCE_GROUP   # prints false when it is gone"
