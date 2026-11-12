#!/usr/bin/env bash
# Check that the DemoStack services needed for a FORTRESS submission are up,
# that tes_nw_wrapper is loaded in dind, and show recent Funnel tasks.
#
# Usage: scripts/fortress/check_stack.sh
set -uo pipefail

DIND="${DIND_CONTAINER:-demostack-dind-1}"
FAIL=0

ok()   { printf '  \033[32mOK\033[0m    %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=1; }

echo "Containers:"
for c in keycloak rabbitmq openldap submissionAPI submissionUI treapi treUI \
         DataEgressAPI DataEgressUI rustfs_submission rustfs_TRE ROCValidAPI \
         demostack-funnel-1 "$DIND"; do
    if docker ps --format '{{.Names}}' | grep -qx "$c"; then ok "$c"; else bad "$c not running"; fi
done

echo "Web endpoints:"
for pair in "Submission Layer|http://localhost:7220" \
            "TRE Admin|http://localhost:8989" \
            "Data Egress|http://localhost:8100" \
            "Funnel API|http://localhost:8000/v1/tasks" \
            "RO-Crate validator|http://localhost:5001"; do
    name="${pair%%|*}"; url="${pair#*|}"
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url")
    # Any response below 500 counts as up, including redirects to login pages.
    if [ "$code" = "000" ]; then
        bad "$name ($url) unreachable"
    elif [ "$code" -ge 500 ]; then
        bad "$name ($url) -> HTTP $code"
    else
        ok "$name ($url) -> HTTP $code"
    fi
done

echo "Image in dind:"
if docker exec "$DIND" docker -H tcp://localhost:2375 image inspect tes_nw_wrapper:latest >/dev/null 2>&1; then
    ok "tes_nw_wrapper:latest"
else
    bad "tes_nw_wrapper:latest not loaded (run scripts/fortress/build_image.sh)"
fi

echo "Recent Funnel tasks:"
curl -s --max-time 5 "http://localhost:8000/v1/tasks?view=BASIC&page_size=5" \
    | python3 -c 'import json,sys
for t in json.load(sys.stdin).get("tasks", []): print("  ", t["id"], t.get("state"), t.get("name"))' \
    2>/dev/null || echo "   (could not query Funnel)"

if [ "$FAIL" -ne 0 ]; then
    echo
    echo "Some checks failed. If containers stopped after a Docker restart, run"
    echo "'docker compose up -d' in 5S-TES-Deployment/DemoStack (see docs/fortress.md, section 1)."
    exit 1
fi
