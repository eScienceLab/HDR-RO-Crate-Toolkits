# Submitting a FORTRESS TES Task

These instructions run the FORTRESS `nw_wrapper.py` help command as a TES task on the 5S-TES DemoStack, then retrieve its output.

## Prerequisites

- Docker Desktop (or Docker Engine with Compose)
- A GitHub account with access to the `UoMResearchIT` FORTRESS image
- Python 3.13+ (only for submitting with the toolkits)

## Quick reference

All demo accounts use the password `password123`.

| Service | URL | Log in as |
| --- | --- | --- |
| Submission Layer | <http://localhost:7220> | `accessfromtretosubmission` for TRE onboarding (step 2); `globaladminuser` for submitting (step 6) |
| TRE Admin | <http://localhost:8989/DeploymentAdmin> | `globaladminuser` |
| Data Egress | <http://localhost:8100> | `globaladminuser` |
| RustFS console (outputs) | <http://localhost:9001> | `globaladminuser`, choosing the Keycloak login option (not the default) |
| Keycloak admin console | <http://localhost:8085/admin> | `admin` / `admin` (not a demo account) |
| Funnel API | <http://localhost:8000/v1/tasks> | No login |

Helper scripts are in [scripts/fortress/](../scripts/fortress/). Run them from the repository root.

| Script | What it does |
| --- | --- |
| `check_stack.sh` | Checks that the required containers and web UIs are up and that `tes_nw_wrapper` is loaded, and lists recent Funnel tasks |
| `build_image.sh` | Pulls the FORTRESS image, builds `tes_nw_wrapper`, and loads it into the dind container (steps 4–5) |
| `setup_toolkit.sh` | Creates `.venv`, installs the toolkits, and creates `.env` and `5s-tes-wb-config.yaml` |

## Steps

### 1. Set up the 5S-TES DemoStack

1. Clone [5S-TES-Deployment](https://github.com/SwanseaUniversityMedical/5S-TES-deployment/)
2. Apply [5s-tes-7369bc4.patch](5s-tes-7369bc4.patch) from the repository root:

    ```bash
    git apply 5s-tes-7369bc4.patch
    ```

    - Note: This patch was created on commit 7369bc4. If conflicts occur when applying the patch, checkout commit 7369bc4 and apply the patch there.

    The patch:
    - fixes the outdated dockerised Funnel setup (`ServiceStack/compose-manifests/tes/`), including a work folder shared with the dind container so that files a task writes to `/outputs` are uploaded
    - adds the RO-Crate validator service (`ServiceStack/compose-manifests/rocrate/`)
    - fixes the capitalisation of a RustFS trusted audience (`Dare-Control-UI-long` to `Dare-Control-UI-Long`)

    If your stack was set up from an earlier version of this patch, re-apply the current one, then continue from step 3. In your 5S-TES-Deployment checkout, this discards any other local changes:

    ```bash
    git checkout -- . && rm -rf ServiceStack/compose-manifests/rocrate
    git apply <path-to>/5s-tes-7369bc4.patch
    ```
3. Start the demo stack:

    ```bash
    cd DemoStack
    docker compose up -d --build
    ```

4. Check the stack. From this repository, run `scripts/fortress/check_stack.sh`. At this point, every check should pass except the `tes_nw_wrapper` image, which you load in step 5.

    If Docker restarts, only containers with `restart: always` come back. Keycloak, RabbitMQ, OpenLDAP and others will be left stopped, and the login pages will break. To recover, run `docker compose up -d` again in `DemoStack`, then restart the dependent services. Restart `tre-api` (container `treapi`) last, after `submissionAPI` reports healthy:

    ```bash
    docker compose restart submissionAPI submissionUI tre-ui DataEgressAPI DataEgressUI
    docker ps --filter name=submissionAPI   # wait for "(healthy)"
    docker compose restart tre-api
    ```

    If `treapi` starts while `submissionAPI` is still down, its TRE Agent never collects submissions. Submissions are accepted but stay on "Waiting for TRE Agent to Transfer" and never reach Funnel. The sign is that `docker logs treapi` shows `ClientHelperRequestAsync Crash with Endpoint http://submissionAPI:8080/...` and no `Execute DEMO DoAgentWork running` lines after it starts. Restarting `treapi` again fixes it.

### 2. Connect the DEMO TRE and approve the project

These steps cover steps 3 and 4 of the [Setup a test environment](https://docs.federated-analytics.ac.uk/tutorials/setup-testenv) tutorial. Skip step 2 of the tutorial, because this setup uses dockerised Funnel.

The DemoStack already contains a TRE called **DEMO** and a project called **Testing**, so you don't need to create either. If you try, **Create TRE** fails with "Another tre already exists with the same admin username". Allow about 2 minutes after startup for the TRE Agent to sync projects.

1. **Download the TRE config from the Submission Layer**
    - Open <http://localhost:7220> and log in as `accessfromtretosubmission`.
    - Open the DEMO TRE and click **Download config**. This saves `tre-onboarding-demo.json`.
    - **Download config** only appears for the TRE's admin user. Other accounts, such as `globaladminuser`, only see **Edit**. If you are already logged in as someone else, log out or use a private browser window.
2. **Upload the config to the TRE Agent**
    - Open <http://localhost:8989/DeploymentAdmin> (the page header reads "| TRE Admin") and log in as `globaladminuser`.
    - This page is in the TRE UI on port 8989. The agent web UI at <http://localhost:3000> doesn't have it.
    - Upload `tre-onboarding-demo.json`.
3. **Check the connection**
    - The button at the top right of the TRE Admin page shows **Sync Active**.
    - In the Submission Layer, DEMO shows as **Online**.
4. **Approve the Testing project's access to the TRE**
    - Follow the [Approve Projects and Memberships](https://docs.federated-analytics.ac.uk/guides/manage-tre/approvals#approve-projects-and-memberships) guide.
    - Check it worked: in the Submission Layer, still logged in as `accessfromtretosubmission`, open the **Testing** project, go to its **TREs** section, and confirm that DEMO's status is **Approved**.

### 3. Log in to GitHub Container Registry

Create a **classic** GitHub personal access token with only the `read:packages` scope. GHCR does not accept fine-grained tokens. If the `UoMResearchIT` organisation uses SSO, click **Configure SSO → Authorize** next to the token.

Log in by passing the token on stdin, which avoids errors from pasting into the hidden password prompt:

```bash
read -s CR_PAT   # paste the token and press Enter (nothing is shown)
echo "$CR_PAT" | docker login ghcr.io -u <github-username> --password-stdin
```

If it worked, Docker prints `Login Succeeded`.

### 4–5. Build `tes_nw_wrapper` and load it into dind

Funnel runs tasks inside the DemoStack's Docker-in-Docker (dind) container, so the image must be built and then loaded there. Run:

```bash
scripts/fortress/build_image.sh
```

The script pulls the FORTRESS image, builds `tes_nw_wrapper` from [tes_nw_wrapper.dockerfile](../scripts/fortress/tes_nw_wrapper.dockerfile), loads it into `demostack-dind-1`, and checks that the load worked. It stops with an error if the dind container isn't running or the pull fails. Loading takes a few minutes, because the image is about 4.7 GB.

- Note: The FORTRESS image is `linux/amd64`. On Apple Silicon the build prints an `InvalidBaseImagePlatform` warning. This is expected: the image runs under emulation, which is slower.

<details>
<summary>Manual steps (what the script runs)</summary>

```bash
docker pull ghcr.io/uomresearchit/rtp-396-nwcybercomm/fortress:main
docker build -t tes_nw_wrapper:latest -f scripts/fortress/tes_nw_wrapper.dockerfile scripts/fortress
docker save tes_nw_wrapper:latest | docker exec -i demostack-dind-1 docker -H tcp://localhost:2375 load
docker exec demostack-dind-1 docker -H tcp://localhost:2375 images tes_nw_wrapper
```

</details>

### 6. Submit the FORTRESS task

Before submitting, check that DEMO shows as **Online** and the Testing project is **Approved** (step 2).

Submit the [FORTRESS Help Task](../tests/data/fortress-5s-tes-pre-submission/tes.json) using either option A or option B.

#### Option A: Submission Layer web UI

Use this option to check that the stack works without any local tooling.

1. Log in to <http://localhost:7220> as **`globaladminuser`**. Don't use `accessfromtretosubmission`: it isn't a member of the Testing project, so **Create Submission** won't appear for it. If you are still logged in from step 2, log out or use a private window.
2. Go to **Projects → Testing → Submissions → Create Submission → TES Wizard**.
3. Set **Submission Mode** to **Raw JSON**, paste the contents of [tes.json](../tests/data/fortress-5s-tes-pre-submission/tes.json), and click **Submit TES Task**.

#### Option B: the toolkits

1. Set up the toolkits:

    ```bash
    scripts/fortress/setup_toolkit.sh
    ```

2. Add the Keycloak client secret. The script created `5s-tes-wb-config.yaml` in the repository root from [5s-tes-wb-config.example.yaml](../scripts/fortress/5s-tes-wb-config.example.yaml). It already has project `Testing`, TRE `DEMO`, the Submission API and the `globaladminuser` login filled in. Git ignores it. Fill in `client_secret` with the secret of the `Dare-Control-API` client. To print it, run:

    ```bash
    python3 -c "import json; print(next(c['secret'] for c in json.load(open('<path-to>/5S-TES-Deployment/DemoStack/config/realm-config/sub-layer.json'))['clients'] if c['clientId']=='Dare-Control-API'))"
    ```

    It is also shown in the Keycloak admin console (<http://localhost:8085/admin>), under **Dare-Control realm → Clients → Dare-Control-API → Credentials**. The admin console doesn't accept the demo accounts. Log in as `admin` with password `admin`, which is set by `KeycloakBootstrapAdminPassword` in `DemoStack/.env`.

    - Note: Use Keycloak credentials, not an access token copied from the Submission UI. A copied token works for submitting but not for `rocrate-tes-fetch` (step 7): RustFS checks every audience in the token, and rejects copied tokens because they include audiences it doesn't trust, such as `realm-management`. With credentials, the Workbench requests an ID token for `Dare-Control-API`, which RustFS accepts. Keep `keycloak_url` as `keycloak.localtest.me`, because the token issuer must match the Keycloak URL that RustFS is configured with.
3. Submit from the repository root:

    ```bash
    .venv/bin/rocrate-tes-submit tests/data/fortress-5s-tes-pre-submission --config_path 5s-tes-wb-config.yaml --disable_roc_validator
    ```

    If it works, the command prints `Task submitted successfully! ID: <n>`. It also writes a submission RO-Crate to `tes-submission-ro-crate/` that records the task ID.

    - Note: `--disable_roc_validator` is currently required. The DemoStack's validator (`ROCValidAPI`, rocrate-validator 0.8.1) only validates against the RO-Crate 1.1 profile, so it rejects this RO-Crate 1.2 crate. It reports a missing `conformsTo` and an unknown `dct:isVersionOf` key. The crate itself is not at fault: the generic `5s-tes-pre-submission` crate fails in the same way.

You can also submit with the [workbench](https://github.com/federated-research/Five-Safes-TES-Workbench) directly. The toolkits use it internally.

### 7. Approve egress and review the results

1. **Track the submission.** In the Submission Layer, open **Testing → Submissions** and select your submission. The status first shows "Waiting for TRE Agent to Transfer" and moves on as the agent syncs, which takes a minute or two. Wait for **Requested Egress**.

    To see whether the task has actually run, run `scripts/fortress/check_stack.sh` or `curl -s "localhost:8000/v1/tasks?view=BASIC"`. A Funnel task named `NW Wrapper` in state `COMPLETE` means the container ran.
2. **Approve egress.** Open <http://localhost:8100>, log in as `globaladminuser`, and approve the output request. It has two files, `nw_wrapper_out.txt` and `nw_wrapper_err.txt`. For details, see the [review output requests guide](https://docs.federated-analytics.ac.uk/guides/manage-tre/approvals).
3. **Get the outputs.**
    - **If you submitted with the toolkits (option B):** run this from the repository root:

        ```bash
        .venv/bin/rocrate-tes-fetch tes-submission-ro-crate --config_path 5s-tes-wb-config.yaml
        ```

        It downloads the outputs into a result RO-Crate at `tes-result-ro-crate/`, containing `nw_wrapper_out.txt`, `nw_wrapper_err.txt`, `tes.json` and `ro-crate-metadata.json`. If it works, the last line is `RO-Crate tes-result-ro-crate created at ...`.
    - **Otherwise:** browse the RustFS console (<http://localhost:9001>). On its login page, choose the Keycloak option, which isn't the default, and log in as `globaladminuser`.

    Once egress is approved, the results are copied to the Submission Layer's output bucket (`12464output` in the RustFS console). Each submission has its own folder, named after the **TRE-level submission ID**. That ID usually differs from the ID shown when you submitted: for example, toolkit task 3 was stored in folder `4`.
4. **Check the output.** `nw_wrapper_out.txt` should contain the wrapper's help text:

    ```text
    usage: nw_wrapper.py [-h] [--scripts-path SCRIPTS_PATH]
                         {finetune,inference,download} ...
    NWCyberComm Wrapper - Simplified interface for finetuning and inference
    ```

## Running real inference

These steps only run the help command. The [FORTRESS repository](https://github.com/UoMResearchIT/RTP-396-nwcybercomm) documents running real inference with a test model through the same DemoStack, including getting `inference-out.jsonl` out through egress, in `Codes/tre_service/running-inference-in-5s-tes.md`. That needs Docker with at least 12 GB of memory, a FORTRESS test image that includes the model, and the shared work folder from the current patch (step 1.2). On an Apple Silicon Mac, a run takes about 50–60 minutes.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `docker login` returns `denied: denied` | GHCR rejected the token. Use a **classic** PAT with `read:packages`, log in with `--password-stdin` (step 3), and check that the token hasn't expired. |
| "This site can't be reached" at `keycloak.localtest.me` | A VPN or local DNS setting is resolving `*.localtest.me` to the wrong address instead of `127.0.0.1`. Disconnect the VPN temporarily, or add `127.0.0.1 keycloak.localtest.me` to your hosts file (`/etc/hosts` on macOS and Linux). |
| Login links or UIs are broken after a Docker restart | Some containers didn't restart. See step 1.4, or run `scripts/fortress/check_stack.sh` to find which ones. |
| **Download config** missing in the Submission Layer | You're logged in as the wrong user. Use `accessfromtretosubmission` (step 2.1). |
| **Create Submission** missing on the Testing project | You're logged in as the wrong user. Use `globaladminuser` (step 6, option A). |
| `rocrate-tes-submit: No such file or directory` | You're not in the repository root. `cd` there first, or run `source .venv/bin/activate`. |
| `WARNING \| Invalid RO-Crate metadata` | The validator only supports RO-Crate 1.1. Add `--disable_roc_validator` (step 6, option B). |
| Submission stays on "Waiting for TRE Agent to Transfer" | The agent may not have synced yet. Check Funnel (step 7.1). If the task is `COMPLETE`, refresh the page after a minute or two. If there's no task, check that DEMO is **Online** and the project is **Approved**. If both are, and Docker or the stack was restarted, `treapi` may have started before `submissionAPI`: restart `treapi` (step 1.4). |
| Blank page at `localhost:8100/signin-oidc` | Sign-in failed with a "Correlation failed" error, because the browser didn't send back the sign-in cookie. Use a private window or Chrome/Firefox, or clear cookies for `localhost` and `keycloak.localtest.me`. Safari is particularly affected over plain http. |
| RustFS console asks for access keys | Choose the Keycloak login option instead of the default, and log in as `globaladminuser`. |
| Task finishes but only `nw_wrapper_out.txt` and `nw_wrapper_err.txt` come back, not files it wrote to `/outputs` | The stack was set up from a patch without the shared Funnel work folder. Re-apply the current patch (step 1.2). |
| `rocrate-tes-fetch` fails with ``STS token exchange failed (403) ... `Dare-Control-UI-Long` is not a trusted audience`` | RustFS's trusted audiences list `Dare-Control-UI-long` (lowercase `l`) in `ServiceStack/compose-manifests/storage/s3-submission.yml`, so tokens copied from the Submission UI are rejected. The current patch fixes this. If your stack predates it, apply the fix by hand (step 1.2). |
| `rocrate-tes-fetch` fails with ``... `realm-management` is not a trusted audience`` | The config uses an access token copied from the Submission UI. Switch to Keycloak credentials and remove `access_token` (step 6, option B). |
