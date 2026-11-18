# HDR RO-Crate Toolkits

Command-line tools for submitting analysis tasks described in [Five Safes RO-Crates](https://github.com/eScienceLab/5s-crate-py) to a Five Safes TES (5S-TES) federated analytics system, and for packaging the results back into an RO-Crate.

## Overview

The toolkit provides two commands:

- **`rocrate-tes-submit`** reads a Five Safes RO-Crate that contains a [GA4GH TES](https://ga4gh.github.io/task-execution-schemas/) task message, optionally validates the crate's metadata, submits the task to 5S-TES and writes a *submission* RO-Crate that records the TES task ID.
- **`rocrate-tes-fetch`** reads a submission RO-Crate, fetches the outputs of its TES task from 5S-TES and writes a *result* RO-Crate containing them.

### 5S-TES and the Workbench

[5S-TES](https://docs.federated-analytics.ac.uk/introduction) is a federated system for running analysis tasks in one or more Trusted Research Environments (TREs) following the Five Safes framework. Tasks are written as GA4GH TES messages and sent to the Submission layer, which checks that the user belongs to the project and queues the task. TRE Agents check the queue, pick up any task allocated to them, and run this against the data in their TRE. Before results leave the TRE, a reviewer must approve their release (egress); approved results are copied to the Submission layer's storage, where the researcher can retrieve them. See [How 5S-TES works](https://docs.federated-analytics.ac.uk/explanations/how-5s-tes-works/architecture) for details.

The toolkit interacts with 5S-TES through the [Five Safes TES Workbench](https://github.com/federated-research/Five-Safes-TES-Workbench) library, which builds and submits TES tasks and fetches their outputs. The Workbench is configured with a YAML file (see [step 4](#4-configure-the-5s-tes-workbench-config-file)) containing the submission layer URL, the target TREs, the object storage details and an access token.

To run a local 5S-TES demonstration stack, follow the [5S-TES test environment tutorial](https://docs.federated-analytics.ac.uk/tutorials/setup-testenv). [docs/fortress.md](docs/fortress.md) walks through a complete example, including a patch that adds the [RO-Crate Validation Service](https://github.com/eScienceLab/RO-Crate-Validation-Service) to the stack.

### RO-Crate validator

Before submitting, `rocrate-tes-submit` sends the crate's metadata to the RO-Crate Validation Service, which checks it against the RO-Crate specification. If validation fails, the task is not submitted.

The service's URL is set by `CRATEY_VALIDATOR_API_URL` (see [step 3](#3-configure-env)). In the demonstration stack the validator runs at `http://localhost:5001`, using the `ghcr.io/esciencelab/ro-crate-validation-service-fivesafes-profile:2.2.1` image. Use `--disable_roc_validator` to skip validation, for example when no validator is available.

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
- [5s-crate-py](https://github.com/eScienceLab/5s-crate-py), from GitHub
- the development dependency `pytest`, if you installed with `".[dev]"`

### 3. Configure .env

Make a copy of `env.template`, rename it to `.env` and populate the variables.

Required variables:
- `CRATEY_VALIDATOR_API_URL`: The URL for the ro-crate validation service. This is `http://localhost:5001` for the demonstration 5S-TES stack.

### 4. Configure the 5S TES Workbench config file

Copy `example-config.yml` from the [Five Safes TES Workbench](https://github.com/federated-research/Five-Safes-TES-Workbench) repo to the repository root, rename it to `5s-tes-wb-config.yaml`, and update the values. The examples below use this name. The path to this file is passed to both commands with `--config_path`.

For the 5S-TES DemoStack, you can instead copy [scripts/fortress/5s-tes-wb-config.example.yaml](scripts/fortress/5s-tes-wb-config.example.yaml) to `5s-tes-wb-config.yaml`. It has the DemoStack settings filled in, so you only need to add the `client_secret` (see [docs/fortress.md](docs/fortress.md), step 6).

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
| `-q`, `--quiet` | Only log warnings and errors |

#### Fetch the results

Once the task has finished, pass the submission RO-Crate to `rocrate-tes-fetch`:

```
rocrate-tes-fetch tes-submission-ro-crate --config_path 5s-tes-wb-config.yaml
```

| Option | Description |
|---|---|
| `--config_path` | Path to the Five Safes TES Workbench config file (required) |
| `--output_rocrate` | Where to write the result RO-Crate. Defaults to `tes-result-ro-crate` in the current directory. |
| `-v`, `--verbose` | Also log debug messages |
| `-q`, `--quiet` | Only log warnings and errors |

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

If something goes wrong, an `ERROR` message explaining the problem is logged to stderr, and the command exits with a non-zero status (see [Exit codes](#8-exit-codes)).

Both commands accept `-v`/`--verbose` to show debug messages and the Five Safes TES Workbench's progress messages, or `-q`/`--quiet` to show only warnings and errors. The two options cannot be used together.

### 8. Exit codes

Both commands exit with a status code that tells scripts and CI pipelines why a run failed. The codes are defined in [`toolkits/config/exit_codes.py`](toolkits/config/exit_codes.py) and listed in each command's `--help` output.

| Code | Name | Meaning | `rocrate-tes-submit` | `rocrate-tes-fetch` |
|---|---|---|:---:|:---:|
| 0 | `SUCCESS` | The command completed successfully | ✓ | ✓ |
| 1 | `GENERAL_ERROR` | An unexpected error occurred | ✓ | ✓ |
| 2 | `USAGE_ERROR` | Invalid command-line arguments | ✓ | ✓ |
| 3 | `INPUT_ERROR` | The input RO-Crate or the Workbench config file is missing or invalid, or the crate has no (or more than one) TES message or task ID | ✓ | ✓ |
| 4 | `VALIDATION_FAILED` | The RO-Crate validator rejected the crate's metadata | ✓ | |
| 5 | `SERVICE_ERROR` | A remote service failed: the RO-Crate validator could not be reached, the TES task could not be built or submitted, or the task outputs could not be fetched | ✓ | ✓ |
| 6 | `OUTPUT_ERROR` | The output RO-Crate could not be created or written, or the output path is inside the input crate | ✓ | ✓ |
| 7 | `NO_RESULTS` | The TES task has no outputs yet, either because it is still running or because it produced no files | | ✓ |

Example: retry `rocrate-tes-fetch` only while the task has no results yet:

```
rocrate-tes-fetch tes-submission-ro-crate --config_path 5s-tes-wb-config.yaml
if [ $? -eq 7 ]; then
    echo "Task not finished yet, try again later"
fi
```
