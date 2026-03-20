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
python -m pip install -e ".[dev]"
```

#### Windows

```
python3 -m venv <virtual_environment_name>
<virtual_environment_name>\Scripts\activate
python -m pip install -e ".[dev]"
```

This installs:
- the package itself
- the `rocrate-to-tes` CLI
- the development dependency `pytest`

### 3. Run the tests

```
pytest -q
```

### 4. Run the tool

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
