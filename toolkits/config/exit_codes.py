from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes shared by the RO-Crate toolkit CLIs."""

    SUCCESS = 0
    GENERAL_ERROR = 1      # Unexpected / uncategorised failure
    USAGE_ERROR = 2        # Invalid CLI arguments (raised by argparse itself)
    INPUT_ERROR = 3        # Input crate or Workbench config missing/unreadable/invalid,
                           # TES message or task ID missing/ambiguous
    VALIDATION_FAILED = 4  # RO-Crate validator rejected the metadata
    SERVICE_ERROR = 5      # Validator API unreachable, TES build/submit failed, or output fetch failed
    OUTPUT_ERROR = 6       # Output crate could not be built or written, or output path nested in input
    NO_RESULTS = 7         # TES task has no outputs yet (still running or produced no files)


EXIT_CODE_DESCRIPTIONS = {
    ExitCode.SUCCESS: "Success",
    ExitCode.GENERAL_ERROR: "Unexpected error",
    ExitCode.USAGE_ERROR: "Invalid command-line arguments",
    ExitCode.INPUT_ERROR: "Input RO-Crate or Workbench config is missing or invalid",
    ExitCode.VALIDATION_FAILED: "RO-Crate validator rejected the metadata",
    ExitCode.SERVICE_ERROR: "RO-Crate validator, TES submission or output fetch failed",
    ExitCode.OUTPUT_ERROR: "Output RO-Crate could not be created or written",
    ExitCode.NO_RESULTS: "TES task has no outputs (still running or produced no files)",
}


def exit_codes_epilog(*codes: ExitCode) -> str:
    """Format the given exit codes as an argparse epilog for `--help`."""

    lines = ["exit codes:"]
    lines += [f"  {code.value}  {EXIT_CODE_DESCRIPTIONS[code]}" for code in codes]
    return "\n".join(lines)
