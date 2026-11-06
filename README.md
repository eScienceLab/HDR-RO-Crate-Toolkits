# HDR RO-Crate Toolkits

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

Copy the `example-config.yml` from the [5S-TES-Workbench](https://github.com/federated-research/5S-TES-Workbench) repo and update the values. The path to this config file will be used when running the `rocrate-tes-submit` command.

### 5. Run the tests

```
pytest -q
```

### 6. Run the tool

The `rocrate-tes-submit` command accepts:
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

### 7. Expected Output

If the tool runs successfully it should print the following information to the terminal:
- 'Validation passed' status, either True or False
- The TES message, as formatted JSON
- The 5S-TES response message, as formatted JSON, which contains the project and task ID's.

Both commands accept `-v`/`--verbose` to show debug messages, or `-q`/`--quiet` to show only warnings and errors. The two options cannot be used together.

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
