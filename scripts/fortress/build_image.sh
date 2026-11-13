#!/usr/bin/env bash
# Build the tes_nw_wrapper image and load it into the DemoStack's
# Docker-in-Docker container, where Funnel runs TES tasks.
#
# Prerequisites: the DemoStack is running and you are logged in to ghcr.io
# (see docs/fortress.md, section 3).
#
# Usage: scripts/fortress/build_image.sh
# Env:   COMPOSE_PROJECT  Compose project name of the DemoStack (default: demostack)
#        DIND_CONTAINER   name of the dind container (default: <project>-dind-1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_IMAGE="ghcr.io/uomresearchit/rtp-396-nwcybercomm/fortress:main"
IMAGE="tes_nw_wrapper:latest"
DIND="${DIND_CONTAINER:-${COMPOSE_PROJECT:-demostack}-dind-1}"
DIND_HOST="tcp://localhost:2375"

if ! docker ps --format '{{.Names}}' | grep -qx "$DIND"; then
    echo "ERROR: container '$DIND' is not running. Start the DemoStack first." >&2
    exit 1
fi

echo "==> Pulling $BASE_IMAGE"
if ! docker pull "$BASE_IMAGE"; then
    echo "ERROR: pull failed. Log in to ghcr.io first (docs/fortress.md, section 3)." >&2
    exit 1
fi

echo "==> Building $IMAGE"
docker build -t "$IMAGE" -f "$SCRIPT_DIR/tes_nw_wrapper.dockerfile" "$SCRIPT_DIR"

echo "==> Loading $IMAGE into $DIND (this can take a few minutes)"
docker save "$IMAGE" | docker exec -i "$DIND" docker -H "$DIND_HOST" load

docker exec "$DIND" docker -H "$DIND_HOST" image inspect "$IMAGE" >/dev/null
echo "==> Done: $IMAGE is available inside $DIND"
