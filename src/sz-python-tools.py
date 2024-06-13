#! /usr/bin/env python3

"""
# -----------------------------------------------------------------------------
# sz-python-tools.py Example python skeleton.
# Can be used as a boiler-plate to build new python scripts.
# This skeleton implements the following features:
#   1) "command subcommand" command line.
#   2) A structured command line parser and "-help"
#   3) Configuration via:
#      3.1) Command line options
#      3.2) Environment variables
#      3.3) Configuration file
#      3.4) Default
#   4) Messages dictionary
#   5) Logging and Log Level support.
#   6) Entry / Exit log messages.
#   7) Docker support.
# -----------------------------------------------------------------------------
"""

# Import from standard library. https://docs.python.org/3/library/

from __future__ import annotations

import argparse
import json
import linecache
import logging
import os
import signal
import sys
import time
from types import FrameType, TracebackType
from typing import Any, Callable, Collection, Dict, List

# Import from https://pypi.org/

# Metadata

__all__: List[str] = []
__version__ = "1.0.0"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = "2019-07-16"
__updated__ = "2022-05-18"

# See https://github.com/senzing-garage/knowledge-base/blob/main/lists/senzing-product-ids.md

SENZING_PRODUCT_ID = "5xxx"
LOG_FORMAT = "%(asctime)s %(message)s"

# Working with bytes.

KILOBYTES = 1024
MEGABYTES = 1024 * KILOBYTES
GIGABYTES = 1024 * MEGABYTES

# The "configuration_locator" describes where configuration variables are in:
# 1) Command line options, 2) Environment variables, 3) Configuration files, 4) Default values

CONFIGURATION_LOCATOR: Dict[
    str,
    Dict[str, bool | str]
    | Dict[str, str | None]
    | Dict[str, str]
    | Dict[str, object]
    | Dict[str, int | str],
] = {
    "debug": {"default": False, "env": "SENZING_DEBUG", "cli": "debug"},
    "password": {"default": None, "env": "SENZING_PASSWORD", "cli": "password"},
    "senzing_dir": {
        "default": "/opt/senzing",
        "env": "SENZING_DIR",
        "cli": "senzing-dir",
    },
    "sleep_time_in_seconds": {
        "default": 0,
        "env": "SENZING_SLEEP_TIME_IN_SECONDS",
        "cli": "sleep-time-in-seconds",
    },
    "subcommand": {
        "default": None,
        "env": "SENZING_SUBCOMMAND",
    },
}

# Enumerate keys in 'configuration_locator' that should not be printed to the log.

KEYS_TO_REDACT: List[str] = [
    "password",
]

# -----------------------------------------------------------------------------
# Define argument parser
# -----------------------------------------------------------------------------


def get_parser() -> argparse.ArgumentParser:
    """Parse commandline arguments."""

    subcommands: Dict[
        str,
        Dict[str, str | List[str] | Dict[str, Dict[str, str]]]
        | Dict[str, str | Dict[str, Dict[str, str]]]
        | Dict[str, str]
        | Dict[str, Collection[str]],
    ] = {
        "task1": {
            "help": "Example task #1.",
            "argument_aspects": ["common"],
            "arguments": {
                "--senzing-dir": {
                    "dest": "senzing_dir",
                    "metavar": "SENZING_DIR",
                    "help": "Location of Senzing. Default: /opt/senzing",
                },
            },
        },
        "task2": {
            "help": "Example task #2.",
            "argument_aspects": ["common"],
            "arguments": {
                "--password": {
                    "dest": "password",
                    "metavar": "SENZING_PASSWORD",
                    "help": "Example of information redacted in the log. Default: None",
                },
            },
        },
        "sleep": {
            "help": "Do nothing but sleep. For Docker testing.",
            "arguments": {
                "--sleep-time-in-seconds": {
                    "dest": "sleep_time_in_seconds",
                    "metavar": "SENZING_SLEEP_TIME_IN_SECONDS",
                    "help": "Sleep time in seconds. DEFAULT: 0 (infinite)",
                },
            },
        },
        "version": {
            "help": "Print version of program.",
        },
        "docker-acceptance-test": {
            "help": "For Docker acceptance testing.",
        },
    }

    # Define argument_aspects.

    argument_aspects: Dict[str, Dict[str, Dict[str, str]]] = {
        "common": {
            "--debug": {
                "dest": "debug",
                "action": "store_true",
                "help": "Enable debugging. (SENZING_DEBUG) Default: False",
            },
            "--engine-configuration-json": {
                "dest": "engine_configuration_json",
                "metavar": "SENZING_ENGINE_CONFIGURATION_JSON",
                "help": "Advanced Senzing engine configuration. Default: none",
            },
        },
    }

    # Augment "subcommands" variable with arguments specified by aspects.

    arguments_key: str = "arguments"
    argument_aspects_key: str = "argument_aspects"
    for subcommand_value in subcommands.values():
        if argument_aspects in subcommand_value:  # type: ignore[comparison-overlap]
            for aspect in subcommand_value[argument_aspects_key]:
                if arguments_key not in subcommand_value:
                    subcommand_value[arguments_key] = {}  # type: ignore[ assignment]
                arguments = argument_aspects.get(aspect, {})
                for argument, argument_value in arguments.items():
                    subcommand_value[arguments_key][argument] = argument_value  # type: ignore[ index]

    parser = argparse.ArgumentParser(
        prog="sz-python-tools.py",
        description="Add description. For more information, see https://github.com/senzing-garage/sz-python-tools",
    )
    subparsers = parser.add_subparsers(
        dest="subcommand", help="Subcommands (SENZING_SUBCOMMAND):"
    )

    for subcommand_key, subcommand_values in subcommands.items():
        subcommand_help = subcommand_values.get("help", "")
        subcommand_arguments = subcommand_values.get("arguments", {})
        subparser = subparsers.add_parser(subcommand_key, help=subcommand_help)  # type: ignore[arg-type]
        for argument_key, argument_values in subcommand_arguments.items():  # type: ignore[attr-defined]
            subparser.add_argument(argument_key, **argument_values)

    return parser


# -----------------------------------------------------------------------------
# Message handling
# -----------------------------------------------------------------------------

# 1xx Informational (i.e. logging.info())
# 3xx Warning (i.e. logging.warning())
# 5xx User configuration issues (either logging.warning() or logging.err() for Client errors)
# 7xx Internal error (i.e. logging.error for Server errors)
# 9xx Debugging (i.e. logging.debug())


MESSAGE_INFO = 100
MESSAGE_WARN = 300
MESSAGE_ERROR = 700
MESSAGE_DEBUG = 900

MESSAGE_DICTIONARY = {
    "100": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}I",
    "292": "Configuration change detected.  Old: {0} New: {1}",
    "293": "For information on warnings and errors, see https://github.com/senzing-garage/stream-loader#errors",
    "294": "Version: {0}  Updated: {1}",
    "295": "Sleeping infinitely.",
    "296": "Sleeping {0} seconds.",
    "297": "Enter {0}",
    "298": "Exit {0}",
    "299": "{0}",
    "300": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}W",
    "499": "{0}",
    "500": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "694": "SENZING_SUBCOMMAND not set: {0}.",
    "695": "Unknown database scheme '{0}' in database url '{1}'",
    "696": "Bad SENZING_SUBCOMMAND: {0}.",
    "697": "No processing done.",
    "698": "Program terminated with error.",
    "699": "{0}",
    "700": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "885": "License has expired.",
    "886": "G2Engine.addRecord() bad return code: {0}; JSON: {1}",
    "888": "G2Engine.addRecord() G2ModuleNotInitialized: {0}; JSON: {1}",
    "889": "G2Engine.addRecord() G2ModuleGenericException: {0}; JSON: {1}",
    "890": "G2Engine.addRecord() Exception: {0}; JSON: {1}",
    "891": "Original and new database URLs do not match. Original URL: {0}; Reconstructed URL: {1}",
    "892": "Could not initialize G2Product with '{0}'. Error: {1}",
    "893": "Could not initialize G2Hasher with '{0}'. Error: {1}",
    "894": "Could not initialize G2Diagnostic with '{0}'. Error: {1}",
    "895": "Could not initialize G2Audit with '{0}'. Error: {1}",
    "896": "Could not initialize G2ConfigMgr with '{0}'. Error: {1}",
    "897": "Could not initialize G2Config with '{0}'. Error: {1}",
    "898": "Could not initialize G2Engine with '{0}'. Error: {1}",
    "899": "{0}",
    "900": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}D",
    "998": "Debugging enabled.",
    "999": "{0}",
}


def message(index: int, *args: Any) -> str:
    """Return an instantiated message."""
    index_string = str(index)
    template = MESSAGE_DICTIONARY.get(
        index_string, "No message for index {0}.".format(index_string)
    )
    return template.format(*args)


def message_generic(generic_index: int, index: int, *args: Any) -> str:
    """Return a formatted message."""
    return "{0} {1}".format(message(generic_index, index), message(index, *args))


def message_info(index: int, *args: Any) -> str:
    """Return an info message."""
    return message_generic(MESSAGE_INFO, index, *args)


def message_warning(index: int, *args: Any) -> str:
    """Return a warning message."""
    return message_generic(MESSAGE_WARN, index, *args)


def message_error(index: int, *args: Any) -> str:
    """Return an error message."""
    return message_generic(MESSAGE_ERROR, index, *args)


def message_debug(index: int, *args: Any) -> str:
    """Return a debug message."""
    return message_generic(MESSAGE_DEBUG, index, *args)


def get_exception() -> (
    Dict[str, str | int | BaseException | type[BaseException] | TracebackType | None]
):
    """Get details about an exception."""
    exception_type, exception_object, traceback = sys.exc_info()
    frame = traceback.tb_frame  # type: ignore[union-attr]
    line_number = traceback.tb_lineno  # type: ignore[union-attr]
    filename = frame.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, line_number, frame.f_globals)
    return {
        "filename": filename,
        "line_number": line_number,
        "line": line.strip(),
        "exception": exception_object,
        "type": exception_type,
        "traceback": traceback,
    }


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def get_configuration(subcommand: str, args: argparse.Namespace) -> Dict[str, Any]:
    """Order of precedence: CLI, OS environment variables, INI file, default."""
    result = {}

    # Copy default values into configuration dictionary.

    for key, value in list(CONFIGURATION_LOCATOR.items()):
        result[key] = value.get("default", None)

    # "Prime the pump" with command line args. This will be done again as the last step.

    for key, value in list(args.__dict__.items()):
        new_key = key.format(subcommand.replace("-", "_"))
        if value:
            result[new_key] = value

    # Copy OS environment variables into configuration dictionary.

    for key, value in list(CONFIGURATION_LOCATOR.items()):
        os_env_var = str(value.get("env", ""))
        if os_env_var:
            os_env_value = os.getenv(os_env_var, None)
            if os_env_value:
                result[key] = os_env_value

    # Copy 'args' into configuration dictionary.

    for key, value in list(args.__dict__.items()):
        new_key = key.format(subcommand.replace("-", "_"))
        if value:
            result[new_key] = value

    # Add program information.

    result["program_version"] = __version__
    result["program_updated"] = __updated__

    # Special case: subcommand from command-line

    if args.subcommand:
        result["subcommand"] = args.subcommand

    # Special case: Change boolean strings to booleans.

    booleans = ["debug"]
    for boolean in booleans:
        boolean_value = result.get(boolean)
        if isinstance(boolean_value, str):
            boolean_value_lower_case = boolean_value.lower()
            if boolean_value_lower_case in ["true", "1", "t", "y", "yes"]:
                result[boolean] = True
            else:
                result[boolean] = False

    # Special case: Change integer strings to integers.

    integers = ["sleep_time_in_seconds"]
    for integer in integers:
        integer_string = result.get(integer, "0")
        result[integer] = int(integer_string)  # type: ignore[call-overload]

    return result


def validate_configuration(config: Dict[Any, Any]) -> None:
    """Check aggregate configuration from commandline options, environment variables, config files, and defaults."""

    user_warning_messages: List[str] = []
    user_error_messages: List[str] = []

    # Perform subcommand specific checking.

    subcommand = config.get("subcommand")

    if subcommand in ["task1", "task2"]:

        if not config.get("senzing_dir"):
            user_error_messages.append(message_error(414))

    # Log warning messages.

    for user_warning_message in user_warning_messages:
        logging.warning(user_warning_message)

    # Log error messages.

    for user_error_message in user_error_messages:
        logging.error(user_error_message)

    # Log where to go for help.

    if len(user_warning_messages) > 0 or len(user_error_messages) > 0:
        logging.info(message_info(293))

    # If there are error messages, exit.

    if len(user_error_messages) > 0:
        exit_error(697)


def redact_configuration(config: Dict[Any, Any]) -> Dict[Any, Any]:
    """Return a shallow copy of config with certain keys removed."""
    result = config.copy()
    for key in KEYS_TO_REDACT:
        try:
            result.pop(key)
        except Exception:
            print(f"Could not pop {key}")
    return result


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------


def bootstrap_signal_handler(signal_number: int, frame: FrameType | None) -> Any:
    """Exit on signal error."""
    logging.debug(message_debug(901, signal_number, frame))
    sys.exit(0)


def create_signal_handler_function(
    args: argparse.Namespace,
) -> Callable[[int, FrameType | None], None]:
    """Tricky code.  Uses currying technique. Create a function for signal handling.
    that knows about "args".
    """

    def result_function(signal_number: int, frame: FrameType | None) -> None:
        logging.info(message_info(298, args))
        logging.debug(message_debug(901, signal_number, frame))
        sys.exit(0)

    return result_function


def entry_template(config: Dict[Any, Any]) -> str:
    """Format of entry message."""
    debug = config.get("debug", False)
    config["start_time"] = time.time()
    if debug:
        final_config = config
    else:
        final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(297, config_json)


def exit_template(config: Dict[Any, Any]) -> str:
    """Format of exit message."""
    debug = config.get("debug", False)
    stop_time = time.time()
    config["stop_time"] = stop_time
    config["elapsed_time"] = stop_time - config.get("start_time", stop_time)
    if debug:
        final_config = config
    else:
        final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(298, config_json)


def exit_error(index: int, *args: Any) -> None:
    """Log error message and exit program."""
    logging.error(message_error(index, *args))
    logging.error(message_error(698))
    sys.exit(1)


def exit_silently() -> None:
    """Exit program."""
    sys.exit(0)


# -----------------------------------------------------------------------------
# do_* functions
#   Common function signature: do_XXX(args)
# -----------------------------------------------------------------------------


def do_docker_acceptance_test(subcommand: str, args: argparse.Namespace) -> None:
    """For use with Docker acceptance testing."""

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(subcommand, args)

    # Prolog.

    logging.info(entry_template(config))

    # Epilog.

    logging.info(exit_template(config))


def do_task1(subcommand: str, args: argparse.Namespace) -> None:
    """Do a task."""

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(subcommand, args)

    # Prolog.

    logging.info(entry_template(config))

    # Do work.

    print("senzing-dir: {senzing_dir}; debug: {debug}".format(**config))

    # Epilog.

    logging.info(exit_template(config))


def do_task2(subcommand: str, args: argparse.Namespace) -> None:
    """Do a task. Print the complete config object"""

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(subcommand, args)

    # Prolog.

    logging.info(entry_template(config))

    # Do work.

    config_json = json.dumps(config, sort_keys=True, indent=4)
    print(config_json)

    # Epilog.

    logging.info(exit_template(config))


def do_sleep(subcommand: str, args: argparse.Namespace) -> None:
    """Sleep.  Used for debugging."""

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(subcommand, args)

    # Prolog.

    logging.info(entry_template(config))

    # Pull values from configuration.

    sleep_time_in_seconds = int(config.get("sleep_time_in_seconds", 0))

    # Sleep.

    if sleep_time_in_seconds > 0:
        logging.info(message_info(296, sleep_time_in_seconds))
        time.sleep(sleep_time_in_seconds)

    else:
        sleep_time_in_seconds = 3600
        while True:
            logging.info(message_info(295))
            time.sleep(sleep_time_in_seconds)

    # Epilog.

    logging.info(exit_template(config))


def do_version(subcommand: str, args: argparse.Namespace) -> None:
    """Log version information."""

    logging.info(message_info(294, __version__, __updated__))
    logging.debug(message_debug(902, subcommand, args))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


if __name__ == "__main__":

    # Configure logging. See https://docs.python.org/2/library/logging.html#levels

    LOG_LEVEL_MAP = {
        "notset": logging.NOTSET,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "fatal": logging.FATAL,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    LOG_LEVEL_PARAMETER = os.getenv("SENZING_LOG_LEVEL", "info").lower()
    LOG_LEVEL = LOG_LEVEL_MAP.get(LOG_LEVEL_PARAMETER, logging.INFO)
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
    logging.debug(message_debug(998))

    # Trap signals temporarily until args are parsed.

    signal.signal(signal.SIGTERM, bootstrap_signal_handler)
    signal.signal(signal.SIGINT, bootstrap_signal_handler)

    # Parse the command line arguments.

    SUBCOMMAND: str = str(os.getenv("SENZING_SUBCOMMAND", None))
    PARSER = get_parser()
    if len(sys.argv) > 1:
        ARGS = PARSER.parse_args()
        SUBCOMMAND = ARGS.subcommand
    elif SUBCOMMAND:
        ARGS = argparse.Namespace(subcommand=SUBCOMMAND)
    else:
        PARSER.print_help()
        if len(os.getenv("SENZING_DOCKER_LAUNCHED", "")) > 0:
            SUBCOMMAND = "sleep"
            ARGS = argparse.Namespace(subcommand=SUBCOMMAND)
            do_sleep(SUBCOMMAND, ARGS)
        exit_silently()

    # Catch interrupts. Tricky code: Uses currying.

    SIGNAL_HANDLER = create_signal_handler_function(ARGS)
    signal.signal(signal.SIGINT, SIGNAL_HANDLER)
    signal.signal(signal.SIGTERM, SIGNAL_HANDLER)

    # Transform subcommand from CLI parameter to function name string.
    if not SUBCOMMAND:
        exit_error(694)
    SUBCOMMAND_FUNCTION_NAME = "do_{0}".format(SUBCOMMAND.replace("-", "_"))

    # Test to see if function exists in the code.

    if SUBCOMMAND_FUNCTION_NAME not in globals():
        logging.warning(message_warning(696, SUBCOMMAND))
        PARSER.print_help()
        exit_silently()

    # Tricky code for calling function based on string.

    globals()[SUBCOMMAND_FUNCTION_NAME](SUBCOMMAND, ARGS)
