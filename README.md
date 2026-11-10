# HDR RO-Crate Toolkits

Command-line tools for submitting analysis tasks described in [Five Safes RO-Crates](https://github.com/eScienceLab/5s-crate-py) to a Five Safes TES (5S-TES) federated analytics system, and for packaging the results back into an RO-Crate.

## Overview

The toolkit provides two commands:

- **`rocrate-tes-submit`** reads a Five Safes RO-Crate that contains a [GA4GH TES](https://ga4gh.github.io/task-execution-schemas/) task message, optionally validates the crate's metadata, submits the task to 5S-TES and writes a *submission* RO-Crate that records the TES task ID.
- **`rocrate-tes-fetch`** reads a submission RO-Crate, fetches the outputs of its TES task from 5S-TES and writes a *result* RO-Crate containing them.

### 5S-TES and the Workbench

[5S-TES](https://docs.federated-analytics.ac.uk/introduction) is a federated system for running analysis tasks in one or more Trusted Research Environments (TREs) following the Five Safes framework. Tasks are written as GA4GH TES messages and sent to the Submission layer, which checks that the user belongs to the project and queues the task. TRE Agents check the queue, pick up any task allocated to them, and run this against the data in their TRE. Before results leave the TRE, a reviewer must approve their release (egress); approved results are copied to the Submission layer's storage, where the researcher can retrieve them. See [How 5S-TES works](https://docs.federated-analytics.ac.uk/explanations/how-5s-tes-works/architecture) for details.

The toolkit interacts with 5S-TES through the [Five Safes TES Workbench](https://github.com/federated-research/Five-Safes-TES-Workbench) library, which builds and submits TES tasks and fetches their outputs. The Workbench is configured with a YAML file (see [step 4](#4-configure-the-5s-tes-workbench-configyml)) containing the submission layer URL, the target TREs, the object storage details and an access token.

To run a local 5S-TES demonstration stack, follow the [5S-TES test environment tutorial](https://docs.federated-analytics.ac.uk/tutorials/setup-testenv). [docs/fortress.md](docs/fortress.md) walks through a complete example, including a patch that adds the [RO-Crate Validation Service](https://github.com/eScienceLab/RO-Crate-Validation-Service) to the stack.

### RO-Crate validator

Before submitting, `rocrate-tes-submit` sends the crate's metadata to the RO-Crate Validation Service, which checks it against the Five Safes RO-Crate profile. If validation fails, the task is not submitted.

The service's URL is set by `CRATEY_VALIDATOR_API_URL` (see [step 3](#3-configure-env)). In the demonstration stack the validator runs at `http://localhost:5001`, using the `ghcr.io/esciencelab/cratey-validator-fivesafes-profile` image. Use `--disable_roc_validator` to skip validation, for example when no validator is available.

## Requirements

```
Python 3.13
```

## Development Setup

### 1. Clone the repo

In the CLI (Git Bash / Terminal):
```
git clone <URL>
cd HDR-RO-Crate-Toolkits
```

### 2. Set up the development environment

Install the project in a virtual environment.

#### Linux / WSL / macOS
```
python3 -m venv <virtual_environment_name>
source <virtual_environment_name>/bin/activate
python -m pip install -e .
```

#### Windows

```
python3 -m venv <virtual_environment_name>
<virtual_environment_name>\Scripts\activate
python -m pip install -e .
```

**NOTE:** For development work you may want to run
```
python -m pip install -e ".[dev]"
```
instead, which also installs the development dependency `pytest`.

This installs:
- the package itself
- the `rocrate-tes-submit` CLI
- the `rocrate-tes-fetch` CLI
- the development dependency `pytest`

Then, install [5s-crate-py](https://github.com/eScienceLab/5s-crate-py) from source.

### 3. Configure .env

Make a copy of `env.template`, rename it to `.env` and populate the variables.

Required variables:
- `CRATEY_VALIDATOR_API_URL`: The URL for the ro-crate validation service. This is `http://localhost:5001` for the demonstration 5S-TES stack.

### 4. Configure the 5S TES Workbench config.yml

Copy the `example-config.yml` from the [Five Safes TES Workbench](https://github.com/federated-research/Five-Safes-TES-Workbench) repo and update the values. The path to this config file is passed to both commands with `--config_path`.

### 5. Run the tests

```
pytest -q
```

### 6. Run the tool

#### Submit a task

`rocrate-tes-submit` accepts:
- a path to `ro-crate-metadata.json`
- a path to a directory containing `ro-crate-metadata.json`
- a path to a ZIP-packaged RO-Crate containing `ro-crate-metadata.json`

```
rocrate-tes-submit ro-crate-metadata.json --config_path 5s-tes-wb-config.yaml
```

Examples:

```
rocrate-tes-submit /path/to/ro-crate-metadata.json --config_path /path/to/5s-tes-wb-config.yaml
rocrate-tes-submit /path/to/ro-crate-directory --config_path /path/to/5s-tes-wb-config.yaml
rocrate-tes-submit /path/to/ro-crate.zip --config_path /path/to/5s-tes-wb-config.yaml
```

| Option | Description |
|---|---|
| `--config_path` | Path to the Five Safes TES Workbench config file (required) |
| `--output_rocrate` | Where to write the submission RO-Crate. Defaults to `tes-submission-ro-crate` in the current directory. Must not be inside the input crate. |
| `--disable_roc_validator` | Skip RO-Crate metadata validation |
| `-v`, `--verbose` | Also log debug messages, including the TES message being submitted |

#### Fetch the results

Once the task has finished, pass the submission RO-Crate to `rocrate-tes-fetch`:

```
rocrate-tes-fetch tes-submission-ro-crate --config_path 5s-tes-wb-config.yaml
```

| Option | Description |
|---|---|
| `--config_path` | Path to the Five Safes TES Workbench config file (required) |
| `--output_dir` | Directory to write the result RO-Crate to. Defaults to the current directory. |
| `--roc_name` | Name of the result RO-Crate directory. Defaults to `tes-result-ro-crate`. |
| `-v`, `--verbose` | Also log debug messages |

### 7. Expected Output

Both commands log their progress to the terminal. Informational messages go to stdout; warnings and errors go to stderr.

A successful `rocrate-tes-submit` run logs:

```
INFO | RO-Crate metadata loaded
INFO | RO-Crate metadata validation successful
INFO | Submitted task ID: 1
INFO | RO-Crate tes-submission-ro-crate created at /path/to/current/directory
```

The validation line is omitted when `--disable_roc_validator` is used. With `-v`, the TES message is also logged as formatted JSON before submission.

The submission RO-Crate is a copy of the input crate with an added action that records the submission and the TES task ID. This crate is the input to `rocrate-tes-fetch`.

A successful `rocrate-tes-fetch` run logs:

```
INFO | RO-Crate loaded
INFO | RO-Crate tes-result-ro-crate created at /path/to/current/directory
```

The result RO-Crate is a copy of the submission crate with the task's output files added, and an action that links the TES message to those outputs.

If something goes wrong, an `ERROR` message explaining the problem is logged to stderr, and the command exits with a non-zero status.
