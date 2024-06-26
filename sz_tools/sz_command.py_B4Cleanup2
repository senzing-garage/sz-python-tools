#! /usr/bin/env python3

""" # TODO """
# TODO Check all outputs using appropriate print_ helper
# TODO Test all completers work


import argparse
import cmd
import configparser
import functools
import glob
import os
import pathlib
import re
import shlex
import sys
import textwrap
import time
from typing import Any, Callable, Dict, List, NoReturn, ParamSpec, TypeVar, Union

from _tool_helpers import (
    Colors,
    colorize_output,
    colorize_str,
    do_help,
    do_history,
    do_responseReformatJson,
    do_responseToClipboard,
    do_responseToFile,
    do_shell,
    get_engine_config,
    history_setup,
    print_error,
    print_info,
    print_response,
    print_warning,
)
from senzing import (  # SzConfig,
    SzConfigManager,
    SzDiagnostic,
    SzEngine,
    SzEngineFlags,
    SzError,
    SzProduct,
)

T = TypeVar("T")
P = ParamSpec("P")
RT = TypeVar("RT")

# Per command JSON formatting options used in decorator
# TODO Add timer?
formatters = [
    "json",
    "jsonl",
    "color",
    "colour",
    "nocolor",
    "nocolour",
]


# -------------------------------------------------------------------------
# Metadata
# -------------------------------------------------------------------------

# TODO Needed for helpers?
__all__ = ["SzCmdShell"]
__version__ = "0.0.1"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = "2024-06-13"
__updated__ = "2024-06-13"


# -------------------------------------------------------------------------
# Decorators
# -------------------------------------------------------------------------


# TODO Wrapped wrapper!
# TODO https://stackoverflow.com/questions/11731136/class-method-decorator-with-self-arguments
# TODO Michal comment
# TODO Typing !
def sz_cmds_decorator(
    cmd_has_args: bool = True,
) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    # TODO
    """Decorator for do_* commands to parse args, display help, set response variables etc."""

    # def decorator(func: Callable[P, T]):  # type: ignore[no-untyped-def]
    def decorator(func: Callable[..., RT]) -> Callable[..., RT]:
        @functools.wraps(func)
        # def wrapper(self, *args, **kwargs):  # type: ignore[no-untyped-def, return]
        def wrapper(self, *args: Any, **kwargs: Any) -> Union[None, RT]:
            cmd_args = args[0]

            # Check if command has formatters for JSON
            if any(x in cmd_args for x in formatters):

                # Capture end of args to detect if formatters are present
                # Reverse the list to use rstrip() to remove formatters
                cmd_formatters = cmd_args[-13:].split(" ")
                cmd_formatters.reverse()

                for format_ in (f for f in cmd_formatters if f.lower() in formatters):
                    if format_.lower() in ["json", "jsonl"]:
                        self.cmd_format = True
                        if format_.lower() == "json":
                            self.format_json_cmd = True
                        if format_.lower() == "jsonl":
                            self.format_json_cmd = False

                    if format_.lower() in ["color", "colour", "nocolor", "nocolour"]:
                        self.cmd_color = True
                        if format_.lower() in ["color", "colour"]:
                            self.color_json_cmd = True
                        if format_.lower() in ["nocolor", "nocolour"]:
                            self.color_json_cmd = False

                    # # Don't remove formatters if we are setting formatting options
                    # if func.__name__ not in ["do_setOutputFormat", "do_setOutputColor"]:
                    #     cmd_args = cmd_args.rstrip(format_).rstrip()  # type: ignore

            if cmd_has_args:
                try:
                    # Parse arguments for a command and add to kwargs
                    # to use in calling method
                    kwargs["parsed_args"] = self.parser.parse_args(
                        [f"{func.__name__[3:]}"] + self.parse(cmd_args)
                    )

                    if "flags" in kwargs["parsed_args"] and kwargs["parsed_args"].flags:
                        kwargs["flags"] = get_engine_flags(kwargs["parsed_args"].flags)

                # Catch argument errors from parser and display the commands help
                except SystemExit:
                    self.do_help(func.__name__)
                    return None
                # Catch parsing errors such as missing single quote around JSON
                # Error is displayed in parse()
                except ValueError:
                    return None
                except KeyError as err:
                    # TODO Test this
                    print_error(err)
                    return None

            # Run the decorated method passing back kwargs for use in SDK call
            try:
                if self.timer:
                    timer_start = time.perf_counter()
                func(self, **kwargs)  # type: ignore
                if self.timer:
                    exec_time = time.perf_counter() - timer_start
                    print_info(
                        f"Approximate execution time (s): {exec_time:.5f}",
                    )
            except (SzError, IOError) as err:
                print_error(err)
            finally:
                # TODO
                self.format_json_cmd = False
                self.color_json_cmd = False
                self.cmd_color = False
                self.cmd_format = False

        return wrapper

    return decorator


# -------------------------------------------------------------------------
# Classes
# -------------------------------------------------------------------------
class SzCommandArgumentParser(argparse.ArgumentParser):
    """Subclass ArgumentParser, override error() with custom message"""

    def error(self, message: str) -> NoReturn:
        self.exit(
            2,
            colorize_output(f"\nERROR: {self.prog} - {message}\n", "error"),
        )


class SzCmdShell(cmd.Cmd):
    """# TODO"""

    def __init__(self, engine_settings: str, debug: bool, args_cli: argparse.Namespace):
        super().__init__()

        # TODO Check all self. are still used
        # TODO Order init vars or leave in groups?

        # Acquire Senzing API engines
        self.debug_trace = debug
        self.engine_settings = engine_settings

        try:
            self.sz_engine = SzEngine(
                "pySzEngine",
                self.engine_settings,
                verbose_logging=self.debug_trace,
            )
            self.sz_product = SzProduct(
                "pySzProduct", self.engine_settings, self.debug_trace
            )
            self.sz_diagnostic = SzDiagnostic(
                "pySzDiagnostic", self.engine_settings, verbose_logging=self.debug_trace
            )
            # self.sz_config = SzConfig(
            #     "pySzConfig", self.engine_settings, verbose_logging=self.debug_trace
            # )
            self.sz_configmgr = SzConfigManager(
                "pySzConfigmgr", self.engine_settings, verbose_logging=self.debug_trace
            )
        except SzError as err:
            print(err)
            sys.exit(1)

        # TODO Move to helpers if repeated
        # Get engine flags for use in auto completion
        self.engine_flags_list = list(SzEngineFlags.__members__.keys())

        # Hide methods - could be deprecated, undocumented, not supported, experimental
        self.__hidden_cmds = (
            "do_EOF",
            "do_findInterestingEntitiesByEntityID",
            "do_findInterestingEntitiesByRecordID",
            "do_getRedoRecord",
            "do_getFeature",
            "do_help",
            "do_hidden",
            "do_shell",
        )

        # Cmd module settings
        self.intro = ""
        self.prompt = "(szcmd) "

        # Readline and history
        self.hist_avail = False
        self.history_disable = args_cli.histDisable
        self.hist_file_name = self.hist_file_error = None

        # For pretty printing JSON responses
        self.cmd_color = False
        self.cmd_format = False
        self.color_json = True
        self.color_json_cmd = False
        self.format_json = False
        self.format_json_cmd = False

        # General
        self.initialized = False
        self.last_response = ""
        self.quit = False
        self.restart = False
        self.restart_debug = False
        self.timer = False

        # Display can't read/write config message once, not at all in container
        self.config_error = 0
        env_launched = os.getenv("SENZING_DOCKER_LAUNCHED", None)
        self.docker_launched = (
            True if env_launched in ("y", "yes", "t", "true", "on", "1") else False
        )

        # -------------------------------------------------------------------------
        # do_* command parsers
        # -------------------------------------------------------------------------

        self.parser = SzCommandArgumentParser(
            add_help=False,
            prog="sz_command",
            usage=argparse.SUPPRESS,
        )
        self.subparsers = self.parser.add_subparsers()

        getConfig_parser = self.subparsers.add_parser(
            "getConfig", usage=argparse.SUPPRESS
        )
        getConfig_parser.add_argument("config_id", type=int)

        # szconfigmanager parsers

        replaceDefaultConfigID_parser = self.subparsers.add_parser(
            "replaceDefaultConfigID", usage=argparse.SUPPRESS
        )
        replaceDefaultConfigID_parser.add_argument(
            "current_default_config_id", type=int
        )
        replaceDefaultConfigID_parser.add_argument("new_default_config_id", type=int)

        setDefaultConfigID_parser = self.subparsers.add_parser(
            "setDefaultConfigID", usage=argparse.SUPPRESS
        )
        setDefaultConfigID_parser.add_argument("config_id", type=int)

        # szdiagnostic parsers

        checkDatastorePerformance_parser = self.subparsers.add_parser(
            "checkDatastorePerformance", usage=argparse.SUPPRESS
        )
        checkDatastorePerformance_parser.add_argument(
            "secondsToRun", default=3, nargs="?", type=int
        )

        getFeature_parser = self.subparsers.add_parser(
            "getFeature", usage=argparse.SUPPRESS
        )
        getFeature_parser.add_argument("featureID", nargs="?", type=int)

        purgeRepository_parser = self.subparsers.add_parser(
            "purgeRepository", usage=argparse.SUPPRESS
        )
        purgeRepository_parser.add_argument(
            "-FORCEPURGE",
            "--FORCEPURGE",
            action="store_true",
            default=False,
            dest="force_purge",
            required=False,
        )

        # szengine parsers

        addRecord_parser = self.subparsers.add_parser(
            "addRecord", usage=argparse.SUPPRESS
        )
        addRecord_parser.add_argument("data_source_code")
        addRecord_parser.add_argument("record_id")
        addRecord_parser.add_argument("record_definition")
        addRecord_parser.add_argument("-f", "--flags", nargs="+", required=False)

        deleteRecord_parser = self.subparsers.add_parser(
            "deleteRecord", usage=argparse.SUPPRESS
        )
        deleteRecord_parser.add_argument("data_source_code")
        deleteRecord_parser.add_argument("record_id")
        deleteRecord_parser.add_argument("-f", "--flags", nargs="+", required=False)

        exportCSVEntityReport_parser = self.subparsers.add_parser(
            "exportCSVEntityReport", usage=argparse.SUPPRESS
        )
        exportCSVEntityReport_parser.add_argument("output_file")
        exportCSVEntityReport_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )
        exportCSVEntityReport_parser.add_argument(
            "-t", "--csv_column_list", required=False, type=str
        )

        exportJSONEntityReport_parser = self.subparsers.add_parser(
            "exportJSONEntityReport", usage=argparse.SUPPRESS
        )
        exportJSONEntityReport_parser.add_argument("output_file")
        exportJSONEntityReport_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        findInterestingEntitiesByEntityID_parser = self.subparsers.add_parser(
            "findInterestingEntitiesByEntityID", usage=argparse.SUPPRESS
        )
        findInterestingEntitiesByEntityID_parser.add_argument("entity_id", type=int)
        findInterestingEntitiesByEntityID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        findInterestingEntitiesByRecordID_parser = self.subparsers.add_parser(
            "findInterestingEntitiesByRecordID", usage=argparse.SUPPRESS
        )
        findInterestingEntitiesByRecordID_parser.add_argument("data_source_code")
        findInterestingEntitiesByRecordID_parser.add_argument("record_id")
        findInterestingEntitiesByRecordID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        # TODO
        # TODO What if a char or non-int is sent?
        def list_of_ints(ints):
            print(list(map(int, ints.split(","))))
            # TODO Comprehension faster?
            return list(map(int, ints.split(",")))

        # TODO Add required False to all parsers
        findNetworkByEntityID_parser = self.subparsers.add_parser(
            "findNetworkByEntityID", usage=argparse.SUPPRESS
        )
        # findNetworkByEntityID_parser.add_argument("entity_list")
        findNetworkByEntityID_parser.add_argument("entity_list", type=list_of_ints)
        findNetworkByEntityID_parser.add_argument("max_degrees", type=int)
        findNetworkByEntityID_parser.add_argument("build_out_degree", type=int)
        findNetworkByEntityID_parser.add_argument("max_entities", type=int)
        findNetworkByEntityID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        # TODO
        def list_of_tuples(rec_keys: str) -> list[tuple[str, str]]:

            error_msg = "error parsing, expecting: 'DATA_SOURCE:RECORD_ID, DATA_SOURCE:RECORD_ID, ...'"

            if "," not in rec_keys or ":" not in rec_keys:
                raise argparse.ArgumentTypeError(error_msg)

            try:
                rec_keys_list = [
                    (values[0].strip(), values[1].strip())
                    for values in (aset.split(":") for aset in rec_keys.split(","))
                ]
                print(rec_keys_list)
            except IndexError as err:
                raise argparse.ArgumentTypeError(error_msg) from err

            return rec_keys_list

        findNetworkByRecordID_parser = self.subparsers.add_parser(
            "findNetworkByRecordID", usage=argparse.SUPPRESS
        )
        # findNetworkByRecordID_parser.add_argument("record_list")
        findNetworkByRecordID_parser.add_argument("record_list", type=list_of_tuples)
        findNetworkByRecordID_parser.add_argument("max_degrees", type=int)
        findNetworkByRecordID_parser.add_argument("build_out_degree", type=int)
        findNetworkByRecordID_parser.add_argument("max_entities", type=int)
        findNetworkByRecordID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        findPathByEntityID_parser = self.subparsers.add_parser(
            "findPathByEntityID", usage=argparse.SUPPRESS
        )
        findPathByEntityID_parser.add_argument("start_entity_id", type=int)
        findPathByEntityID_parser.add_argument("end_entity_id", type=int)
        findPathByEntityID_parser.add_argument("max_degrees", type=int)
        # TODO nargs needs to change if accepting lists instead of json
        findPathByEntityID_parser.add_argument(
            "-e", "--exclusions", default="", nargs="?", required=False
        )
        findPathByEntityID_parser.add_argument(
            "-r", "--required_data_sources", default="", nargs="?", required=False
        )
        findPathByEntityID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        findPathByRecordID_parser = self.subparsers.add_parser(
            "findPathByRecordID", usage=argparse.SUPPRESS
        )
        findPathByRecordID_parser.add_argument("start_data_source_code")
        findPathByRecordID_parser.add_argument("start_record_id")
        findPathByRecordID_parser.add_argument("end_data_source_code")
        findPathByRecordID_parser.add_argument("end_record_id")
        findPathByRecordID_parser.add_argument("max_degrees", type=int)
        # TODO nargs needs to change if accepting lists instead of json
        findPathByRecordID_parser.add_argument(
            "-e", "--exclusions", default="", nargs="?", required=False
        )
        findPathByRecordID_parser.add_argument(
            "-r", "--required_data_sources", default="", nargs="?", required=False
        )
        findPathByRecordID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        getEntityByEntityID_parser = self.subparsers.add_parser(
            "getEntityByEntityID", usage=argparse.SUPPRESS
        )
        getEntityByEntityID_parser.add_argument("entity_id", type=int)
        getEntityByEntityID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        getEntityByRecordID_parser = self.subparsers.add_parser(
            "getEntityByRecordID", usage=argparse.SUPPRESS
        )
        getEntityByRecordID_parser.add_argument("data_source_code")
        getEntityByRecordID_parser.add_argument("record_id")
        getEntityByRecordID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        getRecord_parser = self.subparsers.add_parser(
            "getRecord", usage=argparse.SUPPRESS
        )
        getRecord_parser.add_argument("data_source_code")
        getRecord_parser.add_argument("record_id")
        getRecord_parser.add_argument("-f", "--flags", nargs="+", required=False)

        getVirtualEntityByRecordID_parser = self.subparsers.add_parser(
            "getVirtualEntityByRecordID", usage=argparse.SUPPRESS
        )
        getVirtualEntityByRecordID_parser.add_argument("record_list")
        getVirtualEntityByRecordID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        howEntityByEntityID_parser = self.subparsers.add_parser(
            "howEntityByEntityID", usage=argparse.SUPPRESS
        )
        howEntityByEntityID_parser.add_argument("entity_id", type=int)
        howEntityByEntityID_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        processRedoRecord_parser = self.subparsers.add_parser(
            "processRedoRecord", usage=argparse.SUPPRESS
        )
        processRedoRecord_parser.add_argument("redo_record")
        processRedoRecord_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        reevaluateEntity_parser = self.subparsers.add_parser(
            "reevaluateEntity", usage=argparse.SUPPRESS
        )
        reevaluateEntity_parser.add_argument("entity_id", type=int)
        reevaluateEntity_parser.add_argument("-f", "--flags", required=False, type=int)

        reevaluateRecord_parser = self.subparsers.add_parser(
            "reevaluateRecord", usage=argparse.SUPPRESS
        )
        reevaluateRecord_parser.add_argument("data_source_code")
        reevaluateRecord_parser.add_argument("record_id")
        reevaluateRecord_parser.add_argument("-f", "--flags", required=False, type=int)

        searchByAttributes_parser = self.subparsers.add_parser(
            "searchByAttributes", usage=argparse.SUPPRESS
        )
        searchByAttributes_parser.add_argument("attributes")
        # TODO Remove default
        searchByAttributes_parser.add_argument(
            "search_profile", default="SEARCH", nargs="?"
        )
        searchByAttributes_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        whyEntities_parser = self.subparsers.add_parser(
            "whyEntities", usage=argparse.SUPPRESS
        )
        whyEntities_parser.add_argument("entity_id1", type=int)
        whyEntities_parser.add_argument("entity_id2", type=int)
        whyEntities_parser.add_argument("-f", "--flags", nargs="+", required=False)

        whyRecordInEntity_parser = self.subparsers.add_parser(
            "whyRecordInEntity", usage=argparse.SUPPRESS
        )
        whyRecordInEntity_parser.add_argument("data_source_code")
        whyRecordInEntity_parser.add_argument("record_id")
        whyRecordInEntity_parser.add_argument(
            "-f", "--flags", nargs="+", required=False
        )

        whyRecords_parser = self.subparsers.add_parser(
            "whyRecords", usage=argparse.SUPPRESS
        )
        whyRecords_parser.add_argument("data_source_code1")
        whyRecords_parser.add_argument("record_id1")
        whyRecords_parser.add_argument("data_source_code2")
        whyRecords_parser.add_argument("record_id2")
        whyRecords_parser.add_argument("-f", "--flags", nargs="+", required=False)

        # Utility parsers

        addConfigFile_parser = self.subparsers.add_parser(
            "addConfigFile", usage=argparse.SUPPRESS
        )
        addConfigFile_parser.add_argument("config_json_file")
        addConfigFile_parser.add_argument("config_comments")

        processFile_parser = self.subparsers.add_parser(
            "processFile", usage=argparse.SUPPRESS
        )
        processFile_parser.add_argument("input_file")

        responseToFile_parser = self.subparsers.add_parser(
            "responseToFile", usage=argparse.SUPPRESS
        )
        responseToFile_parser.add_argument("file_path")

        setOutputColor_parser = self.subparsers.add_parser(
            "setOutputColor", usage=argparse.SUPPRESS
        )
        setOutputColor_parser.add_argument("output_color", nargs="?")

        setOutputFormat_parser = self.subparsers.add_parser(
            "setOutputFormat", usage=argparse.SUPPRESS
        )
        setOutputFormat_parser.add_argument("output_format", nargs="?")

        setTheme_parser = self.subparsers.add_parser(
            "setTheme", usage=argparse.SUPPRESS
        )
        setTheme_parser.add_argument(
            "theme", choices=["dark", "default", "light"], nargs=1
        )

    # TODO Explain why doing this
    def output_response(self, response: Union[int, str], color: str = "") -> str:
        """# TODO"""
        return print_response(
            response,
            self.color_json,
            self.color_json_cmd,
            self.format_json,
            self.format_json_cmd,
            self.cmd_color,
            self.cmd_format,
        )

    def completenames(self, text: str, *ignored: Any) -> List[str]:
        """Override function from cmd module to make command completion case-insensitive"""
        do_text = "do_" + text
        return [
            a[3:] for a in self.get_names() if a.lower().startswith(do_text.lower())
        ]

    def get_names(self, include_hidden: bool = False) -> List[str]:
        """
        Override base method in cmd module to return methods for autocomplete and help
        ignoring any hidden commands
        """
        if not include_hidden:
            return [n for n in dir(self.__class__) if n not in self.__hidden_cmds]

        return list(dir(self.__class__))

    def preloop(self) -> None:
        """# TODO"""
        if self.initialized:
            return None

        # TODO
        # if not self.history_disable and READLINE_AVAIL:
        if not self.history_disable:
            history_setup(self)

        # Check if there is a config file and use config
        if not self.docker_launched:
            self.read_config()

        # TODO
        # Initially set theme to use the default colors set by the terminal
        Colors.set_theme("TERMINAL")

        self.initialized = True

        # TODO
        # colorize_output("Welcome to sz_command. Type help or ? for help", "highlight2")
        print_info("Welcome to sz_command. Type help or ? for help")

    def postloop(self) -> None:
        self.initialized = False

    def precmd(self, line: str) -> str:
        return cmd.Cmd.precmd(self, line)

    def postcmd(self, stop: bool, line: str) -> bool:
        # TODO
        # If restart has been requested, set stop value to True to restart engines in main loop
        if self.restart:
            return cmd.Cmd.postcmd(self, True, line)

        return cmd.Cmd.postcmd(self, stop, line)

    @staticmethod
    def do_quit(_) -> bool:  # type: ignore[no-untyped-def]
        """quit command"""
        return True

    def do_exit(self, _) -> bool:  # type: ignore[no-untyped-def]
        """exit command"""
        self.do_quit(self)
        return True

    def ret_quit(self) -> bool:
        """# TODO"""
        return self.quit

    @staticmethod
    def do_EOF(_):  # type: ignore[no-untyped-def] # pylint: disable=invalid-name
        """# TODO"""
        return True

    def emptyline(self) -> bool:
        """Don't do anything if input line was empty"""
        return False

    def default(self, line: str) -> None:
        """Unknown command"""
        print(colorize_output("\nUnknown command, type help or ?\n", "error"))
        return None

    def cmdloop(self, intro: None = None) -> None:
        """# TODO"""
        while True:
            try:
                super(SzCmdShell, self).cmdloop(intro=None)
                # super().cmdloop(intro=None)
                break
            except KeyboardInterrupt:
                if input(
                    colorize_output(
                        "\n\nAre you sure you want to exit? (y/n) ",
                        "caution",
                    )
                ) in ["y", "Y", "yes", "YES"]:
                    break
                else:
                    print()
            except TypeError as err:
                print_error(err)

    # TODO single input commands too
    # TODO Move to helpers for G2ConfigTool? - No, they are different
    # TODO Engines are currently in preloop, move to init?
    def fileloop(self, file_name: str) -> None:
        """# TODO"""
        self.preloop()

        with open(file_name, encoding="utf-8") as data_in:
            for line in data_in:
                line = line.strip()
                # Ignore comments and blank lines
                # if len(line) > 0 and line[0:1] not in ("#", "-", "/"):
                if line and line[0:1] not in ("#", "-", "/"):
                    # *args allows for empty list if there are no args
                    (read_cmd, *args) = line.split()
                    cmd_ = f"do_{read_cmd}"
                    print(f"\n----- {read_cmd} -----")
                    print(f"\n{line}")

                    if cmd_ not in dir(self):
                        print(colorize_output(f"Command {read_cmd} not found", "error"))
                        return None
                    # else:

                    # Join the args into a printable string, format into the command + args to call
                    try:
                        exec_cmd = f'self.{cmd_}({repr(" ".join(args))})'
                        exec(exec_cmd)  # pylint: disable=exec-used
                    except (ValueError, TypeError) as err:
                        print(colorize_output("Command could not be run!", "error"))
                        print_error(err)

    def do_hidden(self, _: None) -> None:
        """# TODO"""
        print()
        print("\n".join(map(str, self.__hidden_cmds)))
        print()

    # ----- Help -----
    # ===== custom help section =====

    def do_help(self, arg: str = "") -> None:
        """# TODO"""
        do_help(self, arg)

    def help_all(self) -> None:
        """# TODO"""
        self.do_help()

    # TODO Check help is still correct
    # @staticmethod
    def help_overview(self) -> None:
        """# TODO"""
        print(
            textwrap.dedent(
                f"""
        {colorize_str('This utility allows you to interact with the Senzing APIs.', 'dim')}

        {colorize_str('Help', 'highlight2')}
            {colorize_str('- View help for a command:', 'dim')} help COMMAND
            {colorize_str('- View all commands:', 'dim')} help all

        {colorize_str('Tab Completion', 'highlight2')}
            {colorize_str('- Tab completion is available for commands, files and engine flags', 'dim')}
            {colorize_str('- Hit tab on a blank line to see all commands', 'dim')}

        {colorize_str('JSON Formatting', 'highlight2')}
            {colorize_str('- Change JSON formatting by adding "json" or "jsonl" to the end of a command', 'dim')}
                - getEntityByEntityID 1001 jsonl

            {colorize_str('- Can be combined with color formatting options', 'dim')}
                - getEntityByEntityID 1001 jsonl nocolor

            {colorize_str('- Set the JSON format for the session, saves the preference to a configuration file for use across sessions', 'dim')}
            {colorize_str('- Specifying the JSON and color formatting options at the end of a command override this setting for that command', 'dim')}
                - setOutputFormat json|jsonl

            {colorize_str('- Convert last response output between json and jsonl', 'dim')}
                - responseReformatJson

        {colorize_str('Color Formatting', 'highlight2')}
            {colorize_str('- Add or remove colors from JSON formatting by adding "color", "colour", "nocolor" or "nocolour" to the end of a command', 'dim')}
                - getEntityByEntityID 1001 color

            {colorize_str('- Can be combined with JSON formatting options', 'dim')}
                - getEntityByEntityID 1001 color jsonl

            {colorize_str('- Set the color formatting for the session, saves the preference to a configuration file for use across sessions', 'dim')}
            {colorize_str('- Specifying the JSON and color formatting options at the end of a command override this setting for that command', 'dim')}
                - setOutputColor color|colour|nocolor|nocolour

        {colorize_str('Capturing Output', 'highlight2')}
            {colorize_str('- Capture the last response output to a file or the clipboard', 'dim')}
                - responseToClipboard
                - responseToFile /tmp/myoutput.json
            {colorize_str('- responseToClipboard does not work in containers or SSH sessions', 'dim')}

        {colorize_str('History', 'highlight2')}
            {colorize_str('- Arrow keys to cycle through history of commands', 'dim')}
            {colorize_str('- Ctrl-r can be used to search history', 'dim')}
            {colorize_str('- Display history:', 'dim')} history

        {colorize_str('Timer', 'highlight2')}
            {colorize_str('- Toggle on/off approximate time a command takes to complete', 'dim')}
            {colorize_str('- Turn off JSON formatting and color output for higher accuracy', 'dim')}
                - timer

        {colorize_str('Shell', 'highlight2')}
            {colorize_str('- Run basic OS shell commands', 'dim')}
                - ! ls

        {colorize_str('Support', 'highlight2')}
            {colorize_str('- Senzing Support:', 'dim')} {colorize_str('https://senzing.zendesk.com/hc/en-us/requests/new', 'highlight1,underline')}
            {colorize_str('- Senzing Knowledge Center:', 'dim')} {colorize_str('https://senzing.zendesk.com/hc/en-us', 'highlight1,underline')}
            {colorize_str('- API Docs:', 'dim')} {colorize_str('https://docs.senzing.com', 'highlight1,underline')}

        """
            )
        )

    def do_shell(self, line: str) -> None:
        """# TODO"""
        do_shell(self, line)

    def do_history(self, _: None) -> None:
        # TODO Check all help <cmd>, not all should have doc strings
        """# TODO"""
        do_history(self, None)

    # -----------------------------------------------------------------------------
    # SDK commands
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    # szconfig commands
    # -----------------------------------------------------------------------------

    # TODO Add a note this isn't an API?
    # TODO Reorder

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getTemplateConfig(self) -> None:
        """
        Get a template configuration

        Syntax:
            getTemplateConfig

        Notes:
            - Use responseToClipboard to send output to clipboard

            - Use responseToFile to send output to a file
        """

        config_handle = self.sz_config.create_config()
        response = self.sz_config.export_config(config_handle)
        self.sz_config.close_config(config_handle)
        self.output_response(response)

    # -----------------------------------------------------------------------------
    # szconfigmanager commands
    # -----------------------------------------------------------------------------

    @sz_cmds_decorator()
    def do_getConfig(
        self, **kwargs: Dict[str, Any]
    ) -> None:  # pylint: disable=invalid-name
        """
        Get a configuration

        Syntax:
            getConfig CONFIG_ID

        Example:
            getConfig 4180061352

        Arguments:
            CONFIG_ID = Configuration identifier

        Notes:
            - Retrieve the active configuration identifier with getActiveConfigID

            - Retrieve a list of configurations and identifiers with getConfigList"""

        response = self.sz_configmgr.get_config(kwargs["parsed_args"].config_id)  # type: ignore
        self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getConfigs(self) -> None:
        """
        Get a list of current configurations

        Syntax:
            getConfigList"""

        response = self.sz_configmgr.get_configs()
        self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getDefaultConfigID(self) -> None:
        """
        Get the default configuration ID

        Syntax:
            getDefaultConfigID"""

        response = self.sz_configmgr.get_default_config_id()
        self.output_response(response, "success")

    @sz_cmds_decorator()
    def do_replaceDefaultConfigID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Replace the default configuration ID

        Syntax:
            replaceDefaultConfigID CURRENT_DEFAULT_CONFIG_ID NEW_DEFAULT_CONFIG_ID

        Example:
            replaceDefaultConfigID 4180061352 2787925967

        Arguments:
            CURRENT_DEFAULT_CONFIG_ID = Configuration identifier
            NEW_DEFAULT_CONFIG_ID = Configuration identifier

        Notes:
            - Retrieve a list of configurations and identifiers with getConfigList"""

        self.sz_configmgr.replace_default_config_id(
            kwargs["parsed_args"].current_default_config_id,
            kwargs["parsed_args"].new_default_config_id,
        )
        self.output_response("New default config set, restarting engines...", "success")
        if self.debug_trace:
            self.do_restartDebug(None)
        else:
            self.do_restart(None)

    @sz_cmds_decorator()
    def do_setDefaultConfigID(self, **kwargs):  # type: ignore[no-untyped-def]
        """
        Set the default configuration ID

        Syntax:
            setDefaultConfigID CONFIG_ID

        Example:
            setDefaultConfigID 4180061352

        Arguments:
            CONFIG_ID = Configuration identifier

        Notes:
            - Retrieve a list of configurations and identifiers with getConfigList"""

        self.sz_configmgr.set_default_config_id(kwargs["parsed_args"].config_id)
        self.output_response("Default config set, restarting engines...", "success")
        if self.debug_trace:
            self.do_restartDebug(None)
        else:
            self.do_restart(None)

    # -----------------------------------------------------------------------------
    # szdiagnostic commands
    # -----------------------------------------------------------------------------

    @sz_cmds_decorator()
    def do_checkDatastorePerformance(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Run a performance check on the database

        Syntax:
            checkDatastorePerformance [SECONDS]
            checkDatastorePerformance

        Arguments:
            SECONDS = Time in seconds to run check, default is 3"""

        response = self.sz_diagnostic.check_datastore_performance(
            kwargs["parsed_args"].secondsToRun
        )
        self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getDatastoreInfo(self) -> None:
        """
        Get data store information

        Syntax:
            getDatastoreInfo"""

        response = self.sz_diagnostic.get_datastore_info()
        self.output_response(response)

    @sz_cmds_decorator()
    def do_getFeature(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Get feature information

        Syntax:
            getFeature FEATURE_ID

        Examples:
            getFeature 1

        Arguments:
            FEATURE_ID = Identifier of feature"""

        response = self.sz_diagnostic.get_feature(kwargs["parsed_args"].featureID)
        self.output_response(response)

    @sz_cmds_decorator()
    def do_purgeRepository(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Purge Senzing database of all data

        Syntax:
            purgeRepository [--FORCEPURGE]

        Example:
            purgeRepository

        Arguments:
            --FORCEPURGE = Don't prompt before purging. USE WITH CAUTION!

        Caution:
            - This deletes all data in the Senzing database!"""

        purge_msg = colorize_output(
            textwrap.dedent(
                """

                ********** WARNING **********

                This will purge all currently loaded data from the senzing database!
                Before proceeding, all instances of senzing (custom code, rest api, redoer, etc.) must be shut down.

                ********** WARNING **********

                Are you sure you want to purge the senzing database? (y/n) """
            ),
            "warning",
        )

        if not kwargs["parsed_args"].force_purge:
            if input(purge_msg) not in ["y", "Y", "yes", "YES"]:
                print()
                return

        self.sz_diagnostic.purge_repository()

    # -----------------------------------------------------------------------------
    # szengine commands
    # -----------------------------------------------------------------------------

    @sz_cmds_decorator()
    def do_addRecord(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Add a record and optionally return information

        Syntax:
            addRecord DSRC_CODE RECORD_ID RECORD_DEFINITION [-f FLAG ...]

        Examples:
            addRecord test 1 '{"NAME_FULL":"Robert Smith", "DATE_OF_BIRTH":"7/4/1976", "PHONE_NUMBER":"787-767-2088"}'
            addRecord test 1 '{"NAME_FULL":"Robert Smith", "DATE_OF_BIRTH":"7/4/1976", "PHONE_NUMBER":"787-767-2088"}' -f SZ_WITH_INFO

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            RECORD_DEFINITION = Senzing mapped JSON representation of a record
            FLAG = Optional space separated list of engine flag(s) to determine output (don't specify for defaults)
        """
        # response = self.sz_engine.add_record(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     kwargs["parsed_args"].record_definition,
        #     **kwargs["flags_dict"],
        # )

        # TODO Consider making all flag using methods partial functions
        if "flags" in kwargs:
            response = self.sz_engine.add_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["parsed_args"].record_definition,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.add_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["parsed_args"].record_definition,
            )

        if response == "{}":
            self.output_response("Record added.", "success")
        else:
            self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_countRedoRecords(self) -> None:
        """
        Counts the number of records in the redo queue

        Syntax:
            countRedoRecords"""

        response = self.sz_engine.count_redo_records()
        if not response:
            self.output_response("No redo records.", "info")
        else:
            self.output_response(response, "success")

    @sz_cmds_decorator()
    def do_deleteRecord(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Delete a record and optionally return information

        Syntax:
            deleteRecord DSRC_CODE RECORD_ID [-f FLAG ...]

        Examples:
            deleteRecord test 1
            deleteRecord test 1 -f SZ_WITH_INFO

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            FLAG = Optional space separated list of engine flag(s) to determine output (don't specify for defaults)
        """

        # response = self.sz_engine.delete_record(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.delete_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.delete_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
            )

        if response == "{}":
            self.output_response("Record deleted.", "success")
        else:
            self.output_response(response)

    # TODO Fix flag names and check all still valid
    # TODO Check available columns for V4
    @sz_cmds_decorator()
    def do_exportCSVEntityReport(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Export repository contents as CSV

        Syntax:
            exportCSVEntityReport OUTPUT_FILE [-t CSV_COLUMN_LIST,...] [-f FLAG ...]

        Examples:
            exportCSVEntityReport export.csv
            exportCSVEntityReport export.csv -t RESOLVED_ENTITY_ID,RELATED_ENTITY_ID,MATCH_LEVEL,MATCH_KEY,DATA_SOURCE,RECORD_ID
            exportCSVEntityReport export.csv -f SZ_EXPORT_INCLUDE_RESOLVED SZ_EXPORT_INCLUDE_POSSIBLY_SAME

        Arguments:
            OUTPUT_FILE = File to save export to
            CSV_COLUMN_LIST = Comma separated list of output columns (don't specify for defaults)
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Available CSV_COLUMNs
                - RESOLVED_ENTITY_ID,RELATED_ENTITY_ID,MATCH_LEVEL,MATCH_KEY,DATA_SOURCE,RECORD_ID,RESOLVED_ENTITY_NAME,RECORD_DEFINITION,ERRULE_CODE

            - Engine flag details https://docs.senzing.com/flags/index.html

        Caution:
            - Export isn't intended for exporting large numbers of entities and associated data source record information.
              Beyond 100M+ data source records isn't suggested. For exporting overview entity and relationship data for
              analytical purposes outside of Senzing please review the following article.

              https://senzing.zendesk.com/hc/en-us/articles/360010716274--Advanced-Replicating-the-Senzing-results-to-a-Data-Warehouse
        """

        rec_cnt = 0

        try:
            with open(
                kwargs["parsed_args"].output_file, "w", encoding="utf-8"
            ) as data_out:
                # export_handle = self.sz_engine.export_csv_entity_report(
                #     kwargs["parsed_args"].csv_column_list, **kwargs["flags_dict"]
                # )

                if "flags" in kwargs:
                    export_handle = self.sz_engine.export_csv_entity_report(
                        kwargs["parsed_args"].csv_column_list, kwargs["flags"]
                    )
                else:
                    export_handle = self.sz_engine.export_csv_entity_report(
                        kwargs["parsed_args"].csv_column_list,
                    )

                while True:
                    export_record = self.sz_engine.fetch_next(export_handle)
                    if not export_record:
                        break
                    data_out.write(export_record)
                    rec_cnt += 1
                    if rec_cnt % 1000 == 0:
                        print(f"Exported {rec_cnt} records...", flush=True)

                self.sz_engine.close_export(export_handle)
        except (SzError, IOError) as err:
            print_error(err)
        else:
            self.output_response(f"Total exported records: {rec_cnt}", "success")

    @sz_cmds_decorator()
    def do_exportJSONEntityReport(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Export repository contents as JSON

        Syntax:
            exportJSONEntityReport OUTPUT_FILE [-f FLAG ...]

        Examples:
            exportJSONEntityReport export.json
            exportJSONEntityReport export.json -f SZ_EXPORT_INCLUDE_RESOLVED SZ_EXPORT_INCLUDE_POSSIBLY_SAME

        Arguments:
            OUTPUT_FILE = File to save export to
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html

        Caution:
            - Export isn't intended for exporting large numbers of entities and associated data source record information.
              Beyond 100M+ data source records isn't suggested. For exporting overview entity and relationship data for
              analytical purposes outside of Senzing please review the following article.

              https://senzing.zendesk.com/hc/en-us/articles/360010716274--Advanced-Replicating-the-Senzing-results-to-a-Data-Warehouse
        """

        rec_cnt = 0

        try:
            with open(
                kwargs["parsed_args"].output_file, "w", encoding="utf-8"
            ) as data_out:
                # export_handle = self.sz_engine.export_json_entity_report(
                #     **kwargs["flags_dict"]
                # )

                if "flags" in kwargs:
                    export_handle = self.sz_engine.export_json_entity_report(
                        kwargs["flags"]
                    )
                else:
                    export_handle = self.sz_engine.export_json_entity_report()

                while True:
                    export_record = self.sz_engine.fetch_next(export_handle)
                    if not export_record:
                        break
                    data_out.write(export_record)
                    rec_cnt += 1
                    if rec_cnt % 1000 == 0:
                        print(f"Exported {rec_cnt} records...", flush=True)

                self.sz_engine.close_export(export_handle)
        except (SzError, IOError) as err:
            print_error(err)
        else:
            self.output_response(f"Total exported records: {rec_cnt}", "success")

    @sz_cmds_decorator()
    def do_findInterestingEntitiesByEntityID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Find interesting entities close to an entity by resolved entity identifier

        Syntax:
            findInterestingEntitiesByEntityID ENTITY_ID [-f FLAG ...]

        Example:
            findInterestingEntitiesByEntityID 1

        Arguments:
            ENTITY_ID = Identifier for an entity
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html

            - Experimental feature requires additional configuration, contact support@senzing.com
        """

        # response = self.sz_engine.find_interesting_entities_by_entity_id(
        #     kwargs["parsed_args"].entity_id, **kwargs["flags_dict"]
        # )

        if "flags" in kwargs:
            response = self.sz_engine.find_interesting_entities_by_entity_id(
                kwargs["parsed_args"].entity_id, kwargs["flags"]
            )
        else:
            response = self.sz_engine.find_interesting_entities_by_entity_id(
                kwargs["parsed_args"].entity_id
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_findInterestingEntitiesByRecordID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Find interesting entities close to an entity by record identifier

        Syntax:
            findInterestingEntitiesByRecordID DSRC_CODE RECORD_ID [-f FLAG ...]

        Example:
            findInterestingEntitiesByRecordID customers 1001

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html

            - Experimental feature requires additional configuration, contact support@senzing.com
        """

        # response = self.sz_engine.find_interesting_entities_by_record_id(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.find_interesting_entities_by_record_id(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.find_interesting_entities_by_record_id(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_findNetworkByEntityID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Find network between entities

        Syntax:
            findNetworkByEntityID ENTITY_LIST MAX_DEGREES BUILD_OUT_DEGREE MAX_ENTITIES [-f FLAG ...]

        Example:
            findNetworkByEntityID '{"ENTITIES":[{"ENTITY_ID":"6"},{"ENTITY_ID":"11"},{"ENTITY_ID":"9"}]}' 4 3 20

        Arguments:
            ENTITY_LIST = JSON document listing entities to find paths between and networks around
            MAX_DEGREES = Maximum number of relationships to search for a path
            BUILD_OUT_DEGREE = Maximum degree of relationships to include around each entity
            MAX_ENTITIES = Maximum number of entities to return
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.find_network_by_entity_id(
        #     kwargs["parsed_args"].entity_list,
        #     kwargs["parsed_args"].max_degrees,
        #     kwargs["parsed_args"].build_out_degree,
        #     kwargs["parsed_args"].max_entities,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.find_network_by_entity_id(
                kwargs["parsed_args"].entity_list,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].build_out_degree,
                kwargs["parsed_args"].max_entities,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.find_network_by_entity_id(
                kwargs["parsed_args"].entity_list,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].build_out_degree,
                kwargs["parsed_args"].max_entities,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_findNetworkByRecordID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Find network between records

        Syntax:
            findNetworkByRecordID RECORD_LIST MAX_DEGREES BUILD_OUT_DEGREE MAX_ENTITIES [-f FLAG ...]

        Example:
            findNetworkByRecordID '{"RECORDS":[{"DATA_SOURCE":"REFERENCE","RECORD_ID":"2071"},{"DATA_SOURCE":"CUSTOMERS","RECORD_ID":"1069"}]}' 6 4 15

        Arguments:
            RECORD_LIST = JSON document listing records to find paths between and networks around
            MAX_DEGREES = Maximum number of relationships to search for a path
            BUILD_OUT_DEGREE = Maximum degree of relationships to include around each entity
            MAX_ENTITIES = Maximum number of entities to return
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.find_network_by_record_id(
        #     kwargs["parsed_args"].record_list,
        #     kwargs["parsed_args"].max_degrees,
        #     kwargs["parsed_args"].build_out_degree,
        #     kwargs["parsed_args"].max_entities,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.find_network_by_record_id(
                kwargs["parsed_args"].record_list,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].build_out_degree,
                kwargs["parsed_args"].max_entities,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.find_network_by_record_id(
                kwargs["parsed_args"].record_list,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].build_out_degree,
                kwargs["parsed_args"].max_entities,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_findPathByEntityID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Find a path between two entities

        Syntax:
            findPathByEntityID START_ENTITY_ID END_ENTITY_ID MAX_DEGREES [-e EXCLUSIONS] [-r REQUIRED_DATA_SOURCES] [-f FLAG ...]

        Example:
            findPathByEntityID 100002 5 3

        Arguments:
            START_ENTITY_ID = Identifier for an entity
            END_ENTITY_ID = Identifier for an entity
            MAX_DEGREES = Maximum number of relationships to search for a path
            EXCLUSIONS = Exclude specified entity IDs or record IDs from the path, default is no exclusions
            REQUIRED_DATA_SOURCES = An entity on the path has specified data source(s), default is no required data sources
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.find_path_by_entity_id(
        #     kwargs["parsed_args"].start_entity_id,
        #     kwargs["parsed_args"].end_entity_id,
        #     kwargs["parsed_args"].max_degrees,
        #     kwargs["parsed_args"].exclusions,
        #     kwargs["parsed_args"].required_data_sources,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.find_path_by_entity_id(
                kwargs["parsed_args"].start_entity_id,
                kwargs["parsed_args"].end_entity_id,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].exclusions,
                kwargs["parsed_args"].required_data_sources,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.find_path_by_entity_id(
                kwargs["parsed_args"].start_entity_id,
                kwargs["parsed_args"].end_entity_id,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].exclusions,
                kwargs["parsed_args"].required_data_sources,
            )

        self.output_response(response)

    # TODO Wording on exclusions
    # TODO Examples with list of entity ids when szengine supports it
    # TODO EXCLUSIONS ... ?
    # TODO Autocomplete data sources? And on other methods?
    @sz_cmds_decorator()
    def do_findPathByRecordID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Find a path between two records

        Syntax:
            findPathByRecordID START_DSRC_CODE START_RECORD_ID END_DSRC_CODE END_RECORD_ID MAX_DEGREES [-e EXCLUSIONS] [-r REQUIRED_DATA_SOURCES] [-f FLAG ...]

        Example:
            findPathByRecordID reference 2141 reference 2121 6

        Arguments:
            START_DSRC_CODE = Data source code
            START_RECORD_ID = Record identifier
            END_DSRC_CODE = Data source code
            END_RECORD_ID = Record identifier
            MAX_DEGREES = Maximum number of relationships to search for a path
            EXCLUSIONS = Exclude specified entity IDs or record IDs from the path, default is no exclusions
            REQUIRED_DATA_SOURCES = An entity on the path has specified data source(s), default is no required data sources
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.find_path_by_record_id(
        #     kwargs["parsed_args"].start_data_source_code,
        #     kwargs["parsed_args"].start_record_id,
        #     kwargs["parsed_args"].end_data_source_code,
        #     kwargs["parsed_args"].end_record_id,
        #     kwargs["parsed_args"].max_degrees,
        #     kwargs["parsed_args"].exclusions,
        #     kwargs["parsed_args"].required_data_sources,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.find_path_by_record_id(
                kwargs["parsed_args"].start_data_source_code,
                kwargs["parsed_args"].start_record_id,
                kwargs["parsed_args"].end_data_source_code,
                kwargs["parsed_args"].end_record_id,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].exclusions,
                kwargs["parsed_args"].required_data_sources,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.find_path_by_record_id(
                kwargs["parsed_args"].start_data_source_code,
                kwargs["parsed_args"].start_record_id,
                kwargs["parsed_args"].end_data_source_code,
                kwargs["parsed_args"].end_record_id,
                kwargs["parsed_args"].max_degrees,
                kwargs["parsed_args"].exclusions,
                kwargs["parsed_args"].required_data_sources,
            )

        self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getActiveConfigID(self) -> None:
        """
        Get the active configuration identifier

        Syntax:
            getActiveConfigID"""

        response = self.sz_engine.get_active_config_id()
        self.output_response(response, "success")

    @sz_cmds_decorator()
    def do_getEntityByEntityID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Get entity by resolved entity identifier

        Syntax:
            getEntityByEntityID ENTITY_ID [-f FLAG ...]

        Examples:
            getEntityByEntityID 1
            getEntityByEntityID 1 -f SZ_ENTITY_BRIEF_DEFAULT_FLAGS SZ_ENTITY_INCLUDE_RECORD_SUMMARY

        Arguments:
            ENTITY_ID = Identifier for an entity
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.get_entity_by_entity_id(
        #     kwargs["parsed_args"].entity_id,
        #     **kwargs["flags_dict"],
        #     # kwargs["parsed_args"].entity_id,
        #     # kwargs["flags"],
        # )
        if "flags" in kwargs:
            response = self.sz_engine.get_entity_by_entity_id(
                kwargs["parsed_args"].entity_id, kwargs["flags"]
            )
        else:
            response = self.sz_engine.get_entity_by_entity_id(
                kwargs["parsed_args"].entity_id
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_getEntityByRecordID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Get entity by data source code and record identifier

        Syntax:
            getEntityByRecordID DSRC_CODE RECORD_ID [-f FLAG ...]

        Examples:
        getEntityByRecordID customers 1001
        getEntityByRecordID customers 1001 -f SZ_ENTITY_BRIEF_DEFAULT_FLAGS SZ_ENTITY_INCLUDE_RECORD_SUMMARY

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.get_entity_by_record_id(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.get_entity_by_record_id(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.get_entity_by_record_id(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_getRecord(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Get a record

        Syntax:
            getRecord DSRC_CODE RECORD_ID [-f FLAG ...]

        Examples:
            getRecord watchlist 2092
            getRecord watchlist 2092 -f SZ_RECORD_DEFAULT_FLAGS SZ_ENTITY_INCLUDE_RECORD_FORMATTED_DATA

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.get_record(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.get_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.get_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
            )

        self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getRedoRecord(self) -> None:
        """
        Get a redo record from the redo queue

        Syntax:
            getRedoRecord"""

        response = self.sz_engine.get_redo_record()
        if not response:
            self.output_response("No redo records.", "info")
        else:
            self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getStats(self) -> None:
        """
        Get engine workload statistics for last process

        Syntax:
            getStats"""

        response = self.sz_engine.get_stats()
        self.last_response = self.output_response(response)

    @sz_cmds_decorator()
    def do_getVirtualEntityByRecordID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Determine how an entity composed of a given set of records would look

        Syntax:
            getVirtualEntityByRecordID RECORD_LIST[-f FLAG ...]

        Example:
            getVirtualEntityByRecordID '{"RECORDS": [{"DATA_SOURCE": "REFERENCE","RECORD_ID": "2071"},{"DATA_SOURCE": "CUSTOMERS","RECORD_ID": "1069"}]}'

        Arguments:
            RECORD_LIST = JSON document listing data sources and records
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.get_virtual_entity_by_record_id(
        #     kwargs["parsed_args"].record_list, **kwargs["flags_dict"]
        # )

        if "flags" in kwargs:
            response = self.sz_engine.get_virtual_entity_by_record_id(
                kwargs["parsed_args"].record_list, kwargs["flags"]
            )
        else:
            response = self.sz_engine.get_virtual_entity_by_record_id(
                kwargs["parsed_args"].record_list,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_howEntityByEntityID(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Retrieve information on how entities are constructed from their records

        Syntax:
            howEntityByEntityID ENTITY_ID [-f FLAG ...]

        Example:
            howEntityByEntityID 96

        Arguments:
            ENTITY_ID = Identifier for an entity
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.how_entity_by_entity_id(
        #     kwargs["parsed_args"].entity_id, **kwargs["flags_dict"]
        # )

        if "flags" in kwargs:
            response = self.sz_engine.how_entity_by_entity_id(
                kwargs["parsed_args"].entity_id, kwargs["flags"]
            )
        else:
            response = self.sz_engine.how_entity_by_entity_id(
                kwargs["parsed_args"].entity_id
            )

        self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_primeEngine(self) -> None:  # type: ignore[no-untyped-def]
        """
        Prime the Senzing engine

        Syntax:
            primeEngine"""

        self.sz_engine.prime_engine()
        self.output_response("Engine primed.", "success")

    @sz_cmds_decorator(cmd_has_args=True)
    def do_processRedoRecord(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Process a redo record fetched from the redo queue

        Syntax:
            processRedoRecord REDO_RECORD [-f FLAG ...]

        Examples:
            processRedoRecord <redo_record>
            processRedoRecord <redo_record> -f SZ_WITH_INFO

        Arguments:
            REDO_RECORD = A redo record
            FLAG = Optional space separated list of engine flag(s) to determine output (don't specify for defaults)
        """

        # response = self.sz_engine.process_redo_record(
        #     kwargs["parsed_args"].redo_record,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.process_redo_record(
                kwargs["parsed_args"].redo_record, kwargs["flags"]
            )
        else:
            response = self.sz_engine.process_redo_record(
                kwargs["parsed_args"].redo_record,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_reevaluateEntity(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Reevaluate an entity and optionally return information

        Syntax:
            reevaluateEntity ENTITY_ID [-f FLAG ...]

        Example:
            reevaluateEntity 1

            reevaluateEntity 1 -f SZ_WITH_INFO

        Arguments:
            ENTITY_ID = Entity identifier
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.reevaluate_entity(
        #     kwargs["parsed_args"].entity_id, **kwargs["flags_dict"]
        # )

        if "flags" in kwargs:
            response = self.sz_engine.reevaluate_entity(
                kwargs["parsed_args"].entity_id, kwargs["flags"]
            )
        else:
            response = self.sz_engine.reevaluate_entity(kwargs["parsed_args"].entity_id)

        # TODO Think about displaying message in all with info methods
        if response == "{}":
            self.output_response("Entity reevaluated.", "success")
        else:
            self.output_response(response)

    @sz_cmds_decorator()
    def do_reevaluateRecord(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Reevaluate a record and optionally return information

        Syntax:
            reevaluateRecord DSRC_CODE RECORD_ID [-f FLAG ...]

        Examples:
            reevaluateRecord customers 1001
            reevaluateRecord customers 1001 -f SZ_WITH_INFO

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.reevaluate_record(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.reevaluate_record(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.reevaluate_record(
                kwargs["parsed_args"].data_source_code, kwargs["parsed_args"].record_id
            )

        if response == "{}":
            self.output_response("Record reevaluated.", "success")
        else:
            self.output_response(response)

    @sz_cmds_decorator()
    def do_searchByAttributes(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        # TODO Should search_profile be documented?
        # searchByAttributes ATTRIBUTES [SEARCH_PROFILE] [-f FLAG ...]
        # searchByAttributes '{"name_full":"Robert Smith", "date_of_birth":"11/12/1978"}' SEARCH -f SZ_SEARCH_BY_ATTRIBUTES_MINIMAL_ALL
        # SEARCH_PROFILE = Search profile to use (defaults to SEARCH)

        """
        Search for entities

        Syntax:
            searchByAttributes ATTRIBUTES [-f FLAG ...]

        Examples:
            searchByAttributes '{"name_full":"Robert Smith", "date_of_birth":"11/12/1978"}'
            searchByAttributes '{"name_full":"Robert Smith", "date_of_birth":"11/12/1978"}' -f SZ_SEARCH_BY_ATTRIBUTES_MINIMAL_ALL

        Arguments:
            ATTRIBUTES = Senzing mapped JSON containing the attributes to search on
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # print(type(kwargs["flags_dict"]))
        # print(kwargs["flags_dict"])
        # print(kwargs["flags_dict"]["flags"].value)
        # response = self.sz_engine.search_by_attributes(
        #     kwargs["parsed_args"].attributes,
        #     # TODO Using like this here due to order of args in szengine
        #     kwargs["flags_dict"]["flags"].value,
        #     kwargs["parsed_args"].search_profile,
        #     # **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.search_by_attributes(
                kwargs["parsed_args"].attributes,
                kwargs["flags"],
                kwargs["parsed_args"].search_profile,
            )
        else:
            response = self.sz_engine.search_by_attributes(
                kwargs["parsed_args"].attributes,
                search_profile=kwargs["parsed_args"].search_profile,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_whyEntities(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Determine how entities relate to each other

        Syntax:
            whyEntities ENTITY_ID1 ENTITY_ID2 [-f FLAG ...]

        Examples:
            whyEntities 96 200011
            whyEntities 96 200011 -f SZ_WHY_ENTITY_DEFAULT_FLAGS SZ_ENTITY_INCLUDE_RECORD_RECORD_DEFINITION

        Arguments:
            ENTITY_ID1 = Identifier for first entity
            ENTITY_ID2 = Identifier for second entity
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.why_entities(
        #     kwargs["parsed_args"].entity_id1,
        #     kwargs["parsed_args"].entity_id2,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.why_entities(
                kwargs["parsed_args"].entity_id1,
                kwargs["parsed_args"].entity_id2,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.why_entities(
                kwargs["parsed_args"].entity_id1,
                kwargs["parsed_args"].entity_id2,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_whyRecordInEntity(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Determine why a particular record resolved to an entity

        Syntax:
            whyRecordInEntity DSRC_CODE RECORD_ID [-f FLAG ...]

        Examples:
            whyRecordInEntity reference 2121
            whyRecordInEntity reference 2121 -f SZ_WHY_ENTITY_DEFAULT_FLAGS SZ_ENTITY_INCLUDE_RECORD_RECORD_DEFINITION

        Arguments:
            DSRC_CODE = Data source code
            RECORD_ID = Record identifier
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.why_record_in_entity(
        #     kwargs["parsed_args"].data_source_code,
        #     kwargs["parsed_args"].record_id,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.why_record_in_entity(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.why_record_in_entity(
                kwargs["parsed_args"].data_source_code,
                kwargs["parsed_args"].record_id,
            )

        self.output_response(response)

    @sz_cmds_decorator()
    def do_whyRecords(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Determine how two records relate to each other

        Syntax:
            whyRecords DSRC_CODE1 RECORD_ID1 DSRC_CODE2 RECORD_ID1 [-f FLAG ...]

        Examples:
            whyRecords reference 2121 watchlist 2092
            whyRecords reference 2121 watchlist 2092 -f SZ_WHY_ENTITY_DEFAULT_FLAGS SZ_ENTITY_INCLUDE_RECORD_RECORD_DEFINITION

        Arguments:
            DSRC_CODE1 = Data source code for first record
            DSRC_CODE2 = Data source code for second record
            RECORD_ID1 = Identifier for first record
            RECORD_ID2 = Identifier for second record
            FLAG = Space separated list of engine flag(s) to determine output (don't specify for defaults)

        Notes:
            - Engine flag details https://docs.senzing.com/flags/index.html"""

        # response = self.sz_engine.why_records(
        #     kwargs["parsed_args"].data_source_code1,
        #     kwargs["parsed_args"].record_id1,
        #     kwargs["parsed_args"].data_source_code2,
        #     kwargs["parsed_args"].record_id2,
        #     **kwargs["flags_dict"],
        # )

        if "flags" in kwargs:
            response = self.sz_engine.why_records(
                kwargs["parsed_args"].data_source_code1,
                kwargs["parsed_args"].record_id1,
                kwargs["parsed_args"].data_source_code2,
                kwargs["parsed_args"].record_id2,
                kwargs["flags"],
            )
        else:
            response = self.sz_engine.why_records(
                kwargs["parsed_args"].data_source_code1,
                kwargs["parsed_args"].record_id1,
                kwargs["parsed_args"].data_source_code2,
                kwargs["parsed_args"].record_id2,
            )

        self.output_response(response)

    # szproduct commands

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getLicense(self) -> None:  # type: ignore[no-untyped-def]
        """
        Get the license information

        Syntax:
            getLicense"""

        response = self.sz_product.get_license()
        self.last_response = self.output_response(response)

    @sz_cmds_decorator(cmd_has_args=False)
    def do_getVersion(self) -> None:  # type: ignore[no-untyped-def]
        """
        Get the version information

        Syntax:
            getVersion"""

        # TODO other places using dumps/loads where doesn't need to?
        # self.printResponse(json.dumps(json.loads(self.sz_product.get_version())))
        self.output_response(self.sz_product.get_version())

    # -----------------------------------------------------------------------------
    # Helper commands
    # -----------------------------------------------------------------------------

    # NOTE This isn't an API call
    # TODO Test
    @sz_cmds_decorator()
    def do_addConfigFile(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Add a configuration from a file

        Syntax:
            addConfigFile CONFIG_FILE 'COMMENTS'

        Example:
            addConfigFile config.json 'Added new features'

        Arguments:
            CONFIG_FILE = File containing configuration to add
            COMMENTS = Comments for the configuration"""

        # fmt: off
        config_add = pathlib.Path(kwargs["parsed_args"].config_json_file).read_text()  # pylint: disable=unspecified-encoding
        # fmt: on
        config_add = config_add.replace("\n", "")
        response = self.sz_configmgr.add_config(
            config_add, kwargs["parsed_args"].config_comments
        )
        self.output_response(f"Configuration added, ID = {response}", "success")

    def do_responseToClipboard(self, _) -> None:  # type: ignore[no-untyped-def]
        """# TODO"""
        do_responseToClipboard(self, None)

    @sz_cmds_decorator()
    def do_responseToFile(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """# TODO"""
        # TODO Change to response_to_file in helpers? And other similar functions
        do_responseToFile(self, **kwargs)

    # TODO Some are arg, others args
    def do_responseReformatJson(self, _) -> None:  # type: ignore[no-untyped-def]
        """# TODO"""
        do_responseReformatJson(self.last_response, self.color_json, self.format_json)

    def do_restart(self, _) -> bool:  # type: ignore[no-untyped-def]
        """# TODO"""
        self.restart = True
        return True

    def do_restartDebug(self, _) -> bool:  # type: ignore[no-untyped-def]
        """# TODO"""
        self.restart_debug = True
        return True

    # TODO Main help is currently wrong
    def do_json_color(self, _: None) -> None:
        # TODO Add to help this saves to config file
        """
        Enables/disables adding colors to JSON responses

        Syntax:
            json_color
        """
        self.color_json = not self.color_json
        print_info(
            f'Coloring of JSON responses {"enabled" if self.color_json else "disabled"}'
        )

        self.write_config()

    # TODO Main help is currently wrong
    def do_json_format(self, _: None) -> None:
        # TODO Add to help this saves to config file
        """
        Switch output between json (tall json) and jsonl (json lines) for JSON responses

        Syntax:
            json_format
        """
        self.format_json = not self.format_json
        print_info(
            f'Formatting of JSON responses {"enabled" if self.format_json else "disabled"}'
        )

        self.write_config()

    # TODO Autocomplete themes?
    # TODO Add themes to config?
    @sz_cmds_decorator()
    def do_setTheme(self, **kwargs):
        """
        Switch terminal ANSI colors between default and light

        Syntax:
            setTheme {default|light}
        """
        Colors.set_theme(kwargs["parsed_args"].theme[0])

    def do_timer(self, _: None) -> None:
        """# TODO"""
        self.timer = not self.timer
        print_info(f'Timer {"enabled" if self.timer else "disabled"}')
        self.write_config()

    # Support methods

    # TODO
    def get_restart(self):
        return self.restart

    def get_restart_debug(self):
        return self.restart_debug

    def parse(self, argument_string):
        """Parses command arguments into a list of argument strings"""

        try:
            shlex_list = shlex.split(argument_string)
            return shlex_list
        except ValueError as err:
            # TODO Move err into f-string
            print_error(err, "Unable to parse arguments")
            raise

    def read_config(self) -> None:
        """# TODO"""
        # TODO Can be used in other tools, e.g. sz_configtool?
        path = pathlib.Path(sys.argv[0])
        file_str = f"~/.{path.stem.lower()}{'.ini'}"
        # TODO expanduser vs resolve, check _tool_helpers where resolve used
        self.config_file = pathlib.Path(file_str).expanduser()
        config_exists = pathlib.Path(self.config_file).exists()
        read_config = configparser.ConfigParser()

        if config_exists:
            try:
                with open(self.config_file, "r", encoding="utf-8") as _:
                    pass
                read_config.read(self.config_file)
                self.format_json = read_config["CONFIG"].getboolean("formatjson")
                self.color_json = read_config["CONFIG"].getboolean("outputcolor")
                self.timer = read_config["CONFIG"].getboolean("timer")
            except IOError as err:
                print_warning(
                    f"Error reading configuration file: {err}",
                )
            except (configparser.Error, KeyError) as err:
                print_warning(
                    f"Error reading entries from configuration file: {err}",
                )
        else:
            # If a configuration file doesn't exist attempt to create one
            self.write_config()

    def write_config(self) -> None:
        """# TODO"""
        if self.docker_launched:
            return

        write_config = configparser.ConfigParser()
        write_config["CONFIG"] = {
            "formatjson": f'{"True" if self.format_json else "False"}',
            "outputcolor": f'{"True" if self.color_json else "False"}',
            "timer": f'{"True" if self.timer else "False"}',
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as config_file:
                write_config.write(config_file)
        except IOError as err:
            # TODO Make a bool
            if self.config_error == 0:
                print_warning(
                    f"Error saving configuration: {err}",
                )
                self.config_error += 1
        except configparser.Error as err:
            if self.config_error == 0:
                print_warning(
                    f"Error writing configuration to the configuration file: {err}",
                )
                self.config_error += 1

    # -------------------------------------------------------------------------
    # Auto completers
    # -------------------------------------------------------------------------

    # TODO Order
    def complete_addRecord(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_deleteRecord(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_exportCSVEntityReport(self, text, line, begidx, endidx):
        if re.match("exportCSVEntityReport +", line) and not re.match(
            "exportCSVEntityReport +.* +", line
        ):
            return self.path_completes(
                text, line, begidx, endidx, "exportCSVEntityReport"
            )

        if re.match(".* -f +", line):
            return self.flags_completes(text, line)

    def complete_exportJSONEntityReport(self, text, line, begidx, endidx):
        if re.match("exportJSONEntityReport +", line) and not re.match(
            "exportJSONEntityReport +.* +", line
        ):
            return self.path_completes(
                text, line, begidx, endidx, "exportJSONEntityReport"
            )

        if re.match(".* -f +", line):
            return self.flags_completes(text, line)

    def complete_findInterestingEntitiesByEntityID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_findInterestingEntitiesByRecordID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_findNetworkByEntityID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_findNetworkByRecordID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_findPathByEntityID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_findPathByRecordID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_getEntityByEntityID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_getEntityByRecordID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_getRecord(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_getVirtualEntityByRecordID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_howEntityByEntityID(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_processRedoRecord(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_reevaluateEntity(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_reevaluateRecord(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_replaceRecord(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_searchByAttributes(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def complete_whyRecordInEntity(self, text, line, begidx, endidx):
        return self.flags_completes(text, line)

    def flags_completes(self, text, line):
        """Auto complete engine flags from szengineflags"""
        if re.match(".* -f +", line):
            return [
                flag
                for flag in self.engine_flags_list
                if flag.lower().startswith(text.lower())
            ]
        return None

    @staticmethod
    def path_completes(text, line, begidx, endidx, callingcmd):
        """Auto complete paths for commands"""

        completes = []
        path_comp = line[len(callingcmd) + 1 : endidx]
        fixed = line[len(callingcmd) + 1 : begidx]
        for path in glob.glob(f"{path_comp}*"):
            path = (
                path + os.sep
                if path and os.path.isdir(path) and path[-1] != os.sep
                else path
            )
            completes.append(path.replace(fixed, "", 1))

        return completes

    def complete_addConfigFile(self, text, line, begidx, endidx):
        if re.match("addConfigFile +", line):
            return self.path_completes(text, line, begidx, endidx, "addConfigFile")

    def complete_responseToFile(self, text, line, begidx, endidx):
        if re.match("responseToFile +", line):
            return self.path_completes(text, line, begidx, endidx, "responseToFile")


# TODO To helpers?
def get_engine_flags(flags: Union[List[str], List[int]]) -> Union[int, None]:
    """Detect if int or named flags are used and convert to int ready to send to SDK call"""

    # For Senzing support team
    if flags[0] == "-1":
        return -1

    # An int is used for the engine flags - old method still support
    # When using an int there should only be one value
    if isinstance(flags[0], int):
        return flags[0]

    # Named engine flag(s) were used, combine and return the int value
    if all(isinstance(f, type(flags[0])) for f in flags[1:]):
        try:
            engine_flags: int = SzEngineFlags.combine_flags(flags)
        except KeyError as err:
            raise KeyError(f"Invalid engine flag: {err}") from err
    else:
        # TODO Test
        # TODO Color? Other places too
        raise TypeError(
            "Invalid type for one or more flag(s), value(s) should be a string"
        )

    return engine_flags


def main(args: argparse.Namespace) -> None:
    """main"""
    first_loop = True
    restart = False

    # Check we can locate an engine configuration
    config = get_engine_config(args.iniFile[0])

    # Execute a file of commands
    # TODO Better way? https://pymotw.com/2/cmd/
    if args.fileToProcess:
        cmd_obj = SzCmdShell(config, args.debugTrace, args.histDisable)
        cmd_obj.fileloop(args.fileToProcess)
    # Start command shell
    else:
        # Don't use args.debugTrace here, may need to restart
        debug_trace = args.debugTrace

        while first_loop or restart:
            # Have we been in the command shell already and are trying to quit? Used for restarting
            if "cmd_obj" in locals() and cmd_obj.ret_quit():
                break

            # TODO
            cmd_obj = SzCmdShell(config, debug_trace, args)
            cmd_obj.cmdloop()

            restart = (
                True if cmd_obj.get_restart() or cmd_obj.get_restart_debug() else False
            )
            debug_trace = True if cmd_obj.get_restart_debug() else False
            first_loop = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "fileToProcess",
        default=None,
        help="path and file name of file with commands to process",
        nargs="?",
    )
    # TODO SzModule.ini for V4?
    parser.add_argument(
        "-c",
        "--iniFile",
        default=[""],
        help="optional path and file name of G2Module.ini to use",
        # TODO Change in all tools, only want 1 item
        nargs=1,
    )
    parser.add_argument(
        "-t",
        "--debugTrace",
        action="store_true",
        default=False,
        help="output debug information",
    )
    parser.add_argument(
        "-H",
        "--histDisable",
        action="store_true",
        default=False,
        help="disable history file usage",
    )

    cli_args = parser.parse_args()
    main(cli_args)
