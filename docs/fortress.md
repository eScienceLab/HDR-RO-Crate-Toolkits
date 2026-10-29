# Submitting a FORTRESS TES Task

## Steps

1. Clone [5S-TES-Deployment](https://github.com/SwanseaUniversityMedical/5S-TES-deployment/)
2. Apply [5s-tes-7369bc4.patch](5s-tes-7369bc4.patch) by
    ```
    git apply 5s-tes-7369bc4.patch
    ```
    - Note: This patch was created on commit 7369bc4. If conflicts occur when applying the patch, checkout commit 7369bc4 and apply the patch there.
3. Start the demo stack and follow steps 3 and 4 in the [Setup a test environment](https://docs.federated-analytics.ac.uk/tutorials/setup-testenv) tutorial. Step 2 is not relevant as we are using dockerised Funnel.
    ```
    cd DemoStack
    docker compose up -d --build
    ```
4. Create a classic GitHub PAT with `read:packages` permission and log in to GHCR 
    ```
    docker login ghcr.io -u <username>
    ```
5. Create `tes_nw_wrapper.dockerfile` and build `tes_nw_wrapper` image
    ```
    docker pull ghcr.io/uomresearchit/rtp-396-nwcybercomm/fortress:main
    docker build -t tes_nw_wrapper . -f tes_nw_wrapper.dockerfile
    ```
    `tes_nw_wrapper.dockerfile`:
    ```
    FROM ghcr.io/uomresearchit/rtp-396-nwcybercomm/fortress:main

    ENTRYPOINT []
    CMD ["/opt/venv/bin/python", "/app/NWCyberComm/nw_wrapper.py", "--scripts-path", "/app/NWCyberComm"]
    ```
6. Copy the image into the dind container
    ```
    docker save tes_nw_wrapper:latest -o /tmp/tes_nw_wrapper.tar && cat /tmp/tes_nw_wrapper.tar | docker exec -i demostack-dind-1 docker -H tcp://localhost:2375 load 2>&1 && rm /tmp/tes_nw_wrapper.tar
    ```
7. Submit the [FORTRESS Help Task](../tests/data/fortress-5s-tes-pre-submission/tes.json) by
    1. following steps 5-7 in the [Setup a test environment](https://docs.federated-analytics.ac.uk/tutorials/setup-testenv) tutorial OR
    2. using the [toolkits](https://github.com/eScienceLab/HDR-RO-Crate-Toolkits) with the [5s-tes-pre-submission](../tests/data/5s-tes-pre-submission/) crate OR
    3. using the [workbench](https://github.com/federated-research/Five-Safes-TES-Workbench)
