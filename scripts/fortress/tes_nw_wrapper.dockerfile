FROM ghcr.io/uomresearchit/rtp-396-nwcybercomm/fortress:main

ENTRYPOINT []
CMD ["/opt/venv/bin/python", "/app/NWCyberComm/nw_wrapper.py", "--scripts-path", "/app/NWCyberComm"]
