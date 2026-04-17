# HDR RO-Crate Toolkits

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
- `TES_SUBMISSION_API_URL`: The URL for the 5S-TES submission API. This is `http://localhost:5034` for the demonstration 5S-TES stack.
- `TES_SUBMISSION_API_TOKEN`: The API token for accessing the 5S-TES submission API. This can be obtained from the submission layer webpage.

### 4. Run the tests

```
pytest -q
```

### 5. Run the tool

The `rocrate-to-tes` command accepts:
- a path to `ro-crate-metadata.json`
- a path to a directory containing `ro-crate-metadata.json`
- a path to a ZIP-packaged RO-Crate containing `ro-crate-metadata.json`

```
rocrate-to-tes ro-crate-metadata.json
```

Examples:

```
rocrate-to-tes /path/to/ro-crate-metadata.json
rocrate-to-tes /path/to/ro-crate-directory
rocrate-to-tes /path/to/ro-crate.zip
```

### 6. Expected Output

If the tool runs successfully it should print the following information to the terminal:
- 'Validation passed' status, either True or False
- The TES message, as formatted JSON
- The 5S-TES response message, as formatted JSON, which contains the project and task ID's.