#!/usr/bin/env bash
# Idempotent deploy of the issue-triage MCP server to Azure Container Apps.
#
#   RG -> ACR + Container Apps environment + app (bootstrap placeholder) -> remote image build
#      -> app switched to the real image -> wait until healthy
#
# stdout: ONLY the final MCP endpoint (https://<fqdn>/mcp). Progress goes to stderr.
# The API key is read from (or generated into) .env.local and is never printed.
#
# Options:  --what-if   preview the Bicep changes (az deployment group what-if) and exit
# Env:      RESOURCE_GROUP (rg-csharness-lab)  LOCATION (koreacentral)  DELETE_AFTER (2026-10-24)
#           IMAGE_REPO (csharness-mcp)         HEALTH_TIMEOUT_SEC (600)
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-csharness-lab}"
LOCATION="${LOCATION:-koreacentral}"
DELETE_AFTER="${DELETE_AFTER:-2026-10-24}"
IMAGE_REPO="${IMAGE_REPO:-csharness-mcp}"
HEALTH_TIMEOUT_SEC="${HEALTH_TIMEOUT_SEC:-600}"
PARAMS_FILE="$LAB_DIR/infra/main.bicepparam"
RUN_DIR="$LAB_DIR/.run"

WHAT_IF=0
case "${1:-}" in
  "") ;;
  --what-if) WHAT_IF=1 ;;
  -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) die "unknown option: $1 (see --help)" ;;
esac

command -v az >/dev/null 2>&1 || die "Azure CLI (az) is required"
command -v curl >/dev/null 2>&1 || die "curl is required"
mkdir -p "$RUN_DIR"

# 0. Which subscription are we about to touch?
if ! ACCOUNT="$(az account show --query "join('|', [name, id, tenantId, user.name])" -o tsv 2>/dev/null)"; then
  die "Not logged in to Azure. Run 'az login' (and 'az account set -s <subscription>') first."
fi
IFS='|' read -r SUB_NAME SUB_ID TENANT_ID USER_NAME <<<"$ACCOUNT"
log "[az] subscription: $SUB_NAME ($SUB_ID)"
log "[az] tenant: $TENANT_ID / user: $USER_NAME"

# 1. Inputs: build-time copies of the shared classifier + the API key
sync_shared
ensure_api_key
API_KEY="$(env_get API_KEY)"
KEY_FINGERPRINT="$(printf '%s' "$API_KEY" | sha256 | cut -c1-12)"
TAG="$(content_hash)"

# 2. Resource providers
for ns in Microsoft.App Microsoft.ContainerRegistry Microsoft.OperationalInsights; do
  state="$(az provider show -n "$ns" --query registrationState -o tsv 2>/dev/null || echo Unknown)"
  if [[ "$state" != "Registered" ]]; then
    log "[provider] registering $ns (was: $state) ..."
    az provider register -n "$ns" --wait -o none
  fi
done

# 3. Resource group (reuse its location if it already exists)
if [[ "$(az group exists -n "$RESOURCE_GROUP")" == "true" ]]; then
  LOCATION="$(az group show -n "$RESOURCE_GROUP" --query location -o tsv)"
  log "[rg] $RESOURCE_GROUP exists in $LOCATION"
  az tag update --resource-id "/subscriptions/$SUB_ID/resourceGroups/$RESOURCE_GROUP" --operation merge \
    --tags purpose=copilot-studio-harness-lab deleteAfter="$DELETE_AFTER" -o none
else
  log "[rg] creating $RESOURCE_GROUP in $LOCATION"
  az group create -n "$RESOURCE_GROUP" -l "$LOCATION" \
    --tags purpose=copilot-studio-harness-lab deleteAfter="$DELETE_AFTER" -o none
fi

# deploy <image-tag-or-empty> <deployment-name> <az args...>
# The key travels through the environment (read by main.bicepparam), never through argv.
deploy() {
  local image_tag="$1" name="$2"; shift 2
  API_KEY="$API_KEY" IMAGE_TAG="$image_tag" KEY_FINGERPRINT="$KEY_FINGERPRINT" DELETE_AFTER="$DELETE_AFTER" \
    az deployment group "$@" -g "$RESOURCE_GROUP" -n "$name" --parameters "$PARAMS_FILE"
}

resource_name() { az resource list -g "$RESOURCE_GROUP" --resource-type "$1" --query '[0].name' -o tsv; }

APP_NAME="$(resource_name Microsoft.App/containerApps)"

if [[ "$WHAT_IF" == "1" ]]; then
  [[ -z "$APP_NAME" ]] && WHAT_IF_TAG="" || WHAT_IF_TAG="$TAG"
  log "[what-if] image tag: '${WHAT_IF_TAG:-<bootstrap>}'"
  deploy "$WHAT_IF_TAG" "csharness-whatif" what-if >&2
  exit 0
fi

# 4. Phase 1 (bootstrap): registry + environment + app on a placeholder image + AcrPull for its identity
if [[ -z "$APP_NAME" ]]; then
  log "[bicep] phase 1/2: ACR + environment + app (placeholder image) ..."
  deploy "" "csharness-bootstrap" create -o none
  APP_NAME="$(resource_name Microsoft.App/containerApps)"
else
  log "[bicep] container app '$APP_NAME' already exists -> skipping phase 1"
fi
ACR_NAME="$(resource_name Microsoft.ContainerRegistry/registries)"
[[ -n "$ACR_NAME" && -n "$APP_NAME" ]] || die "ACR or container app not found in $RESOURCE_GROUP"
log "[bicep] registry: $ACR_NAME / app: $APP_NAME"

# 5. Remote image build (ACR Tasks) - skipped when this exact source is already in the registry
if az acr repository show -n "$ACR_NAME" --image "$IMAGE_REPO:$TAG" -o none 2>/dev/null; then
  log "[acr] $IMAGE_REPO:$TAG already in the registry -> skipping build"
else
  log "[acr] az acr build -> $ACR_NAME/$IMAGE_REPO:$TAG (remote build, no local Docker)"
  az acr build -r "$ACR_NAME" -t "$IMAGE_REPO:$TAG" "$SERVER_DIR" 2>&1 | tee "$RUN_DIR/acr-build.log" >&2
  log "[acr] $(grep -E 'Run ID: .* was successful' "$RUN_DIR/acr-build.log" | tail -n 1 || true)"
fi
log "[acr] digest: $(az acr repository show -n "$ACR_NAME" --image "$IMAGE_REPO:$TAG" --query digest -o tsv)"

# 6. Phase 2: switch the app to the real image (also rolls a new revision when the key changed)
log "[bicep] phase 2/2: app -> $IMAGE_REPO:$TAG"
FQDN="$(deploy "$TAG" "csharness-app-$TAG" create --query properties.outputs.fqdn.value -o tsv)"
[[ -n "$FQDN" ]] || die "deployment did not return an FQDN"

# 7. Wait until the newest revision is ready and /healthz answers "ok"
deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SEC ))
log "[wait] https://$FQDN/healthz (timeout ${HEALTH_TIMEOUT_SEC}s)"
while :; do
  state="$(az resource show -g "$RESOURCE_GROUP" -n "$APP_NAME" --resource-type Microsoft.App/containerApps \
    --query "join('|', [properties.provisioningState || '', properties.latestRevisionName || '', properties.latestReadyRevisionName || ''])" \
    -o tsv 2>/dev/null || true)"
  IFS='|' read -r prov latest ready <<<"$state"
  body="$(curl -fsS --max-time 10 "https://$FQDN/healthz" 2>/dev/null || true)"
  log "[wait] provisioning=${prov:-?} latest=${latest:-?} ready=${ready:-?} healthz=${body:-<none>}"
  if [[ "${prov:-}" == "Succeeded" && -n "${latest:-}" && "${latest:-}" == "${ready:-}" && "$body" == "ok" ]]; then
    break
  fi
  if (( $(date +%s) >= deadline )); then
    die "not healthy after ${HEALTH_TIMEOUT_SEC}s. Inspect: az containerapp logs show -g $RESOURCE_GROUP -n $APP_NAME --type system"
  fi
  sleep 10
done

env_set MCP_ENDPOINT "https://$FQDN/mcp"
log "[done] revision $ready is healthy. Endpoint saved to .env.local (MCP_ENDPOINT); API key stays in .env.local."
printf 'https://%s/mcp\n' "$FQDN"
