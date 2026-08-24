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

This installs:
- the package itself
- the `rocrate-to-tes` CLI
- the development dependency `pytest`


**NOTE:** For development work you may want to run
```
python -m pip install -e ".[dev]"
```
instead, which also installs the development dependency `pytest`.

### 3. Configure .env

Make a copy of `env.template`, rename it to `.env` and populate the variables.

Required variables:
- `CRATEY_VALIDATOR_API_URL`: The URL for the ro-crate validation service. This is `http://localhost:5001` for the demonstration 5S-TES stack.

### 4. Configure the 5S TES Workbench config.yml

Copy the `example-config.yml` from the [5S-TES-Workbench](https://github.com/federated-research/5S-TES-Workbench) repo and update the values. The path to this config file will be used when running the `rocrate-to-tes` command.

### 5. Run the tests

```
pytest -q
```

### 6. Run the tool

The `rocrate-to-tes` command accepts:
- a path to `ro-crate-metadata.json`
- a path to a directory containing `ro-crate-metadata.json`
- a path to a ZIP-packaged RO-Crate containing `ro-crate-metadata.json`

```
rocrate-to-tes ro-crate-metadata.json --config_path 5s-tes-wb-config.yaml
```

Examples:

```
rocrate-to-tes /path/to/ro-crate-metadata.json --config_path /path/to/5s-tes-wb-config.yaml
rocrate-to-tes /path/to/ro-crate-directory --config_path /path/to/5s-tes-wb-config.yaml
rocrate-to-tes /path/to/ro-crate.zip --config_path /path/to/5s-tes-wb-config.yaml
```

### 7. Expected Output

If the tool runs successfully it should print the following information to the terminal:
- 'Validation passed' status, either True or False
- The TES message, as formatted JSON
- The 5S-TES response message, as formatted JSON, which contains the project and task ID's.