"""
# TODO
"""

from __future__ import annotations

import cmd
import configparser
import os
import re
import sys
import textwrap
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union

READLINE_AVAIL = False
with suppress(ImportError):
    import atexit
    import readline

    READLINE_AVAIL = True


ORJSON_AVAIL = False
try:
    import orjson  # type: ignore

    JsonDecodeError = orjson.JSONDecodeError
    ORJSON_AVAIL = True
except ImportError:
    import json

    JsonDecodeError = json.decoder.JSONDecodeError

PYCLIP_AVAIL = False
with suppress(ImportError):
    import pyclip
    from pyclip import ClipboardSetupException

    PYCLIP_AVAIL = True

if TYPE_CHECKING:
    from sz_command import SzCmdShell
    from sz_configtool import SzCfgShell

# TODO Change to sz when changed in builds
CONFIG_FILE = "G2Module.ini"

# -------------------------------------------------------------------------
# Helper classes
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# Classes for handling colors
# -------------------------------------------------------------------------


class Colors:
    """# TODO"""

    @classmethod
    def apply(cls, to_color: Union[int, str], colors_list: str = "") -> Union[int, str]:
        # TODO
        """apply list of colors to a string"""
        # TODO colors_list is a string with multiple entries separated by ,
        if colors_list:
            prefix = "".join(
                [getattr(cls, i.strip().upper()) for i in colors_list.split(",")]
            )
            return f"{prefix}{to_color}{cls.RESET}"

        return to_color

    @classmethod
    def set_theme(cls, theme: str) -> None:
        """# TODO"""
        # best for dark backgrounds
        if theme.upper() == "DEFAULT":
            cls.TABLE_TITLE = cls.FG_GREY42
            cls.ROW_TITLE = cls.FG_GREY42
            cls.COLUMN_HEADER = cls.FG_GREY42
            cls.ENTITY_COLOR = cls.SZ_PURPLE  # cls.FG_MEDIUMORCHID1
            cls.DSRC_COLOR = cls.SZ_ORANGE  # cls.FG_ORANGERED1
            cls.ATTR_COLOR = cls.SZ_BLUE  # cls.FG_CORNFLOWERBLUE
            cls.GOOD = cls.SZ_GREEN  # cls.FG_CHARTREUSE3
            cls.BAD = cls.SZ_RED  # cls.FG_RED3
            cls.CAUTION = cls.SZ_YELLOW  # cls.FG_GOLD3
            cls.HIGHLIGHT1 = cls.SZ_PINK  # cls.FG_DEEPPINK4
            cls.HIGHLIGHT2 = cls.SZ_CYAN  # cls.FG_DEEPSKYBLUE1
            cls.MATCH = cls.SZ_BLUE
            cls.AMBIGUOUS = cls.SZ_LIGHTORANGE
            cls.POSSIBLE = cls.SZ_ORANGE
            cls.RELATED = cls.SZ_GREEN
            cls.DISCLOSED = cls.SZ_PURPLE
        elif theme.upper() == "LIGHT":
            cls.TABLE_TITLE = cls.FG_LIGHTBLACK
            cls.ROW_TITLE = cls.FG_LIGHTBLACK
            cls.COLUMN_HEADER = cls.FG_LIGHTBLACK  # + cls.ITALICS
            cls.ENTITY_COLOR = cls.FG_LIGHTMAGENTA + cls.BOLD
            cls.DSRC_COLOR = cls.FG_LIGHTYELLOW + cls.BOLD
            cls.ATTR_COLOR = cls.FG_LIGHTCYAN + cls.BOLD
            cls.GOOD = cls.FG_LIGHTGREEN
            cls.BAD = cls.FG_LIGHTRED
            cls.CAUTION = cls.FG_LIGHTYELLOW
            cls.HIGHLIGHT1 = cls.FG_LIGHTMAGENTA
            cls.HIGHLIGHT2 = cls.FG_LIGHTCYAN
            cls.MATCH = cls.FG_LIGHTBLUE
            cls.AMBIGUOUS = cls.FG_LIGHTYELLOW
            cls.RELATED = cls.FG_LIGHTGREEN
            cls.DISCLOSED = cls.FG_LIGHTMAGENTA
        elif theme.upper() == "DARK":
            cls.TABLE_TITLE = cls.FG_BLACK
            cls.ROW_TITLE = cls.FG_BLACK
            cls.COLUMN_HEADER = cls.FG_BLACK  # + cls.ITALICS
            cls.ENTITY_COLOR = cls.FG_MAGENTA
            cls.DSRC_COLOR = cls.FG_YELLOW
            cls.ATTR_COLOR = cls.FG_CYAN
            cls.GOOD = cls.FG_GREEN
            cls.BAD = cls.FG_RED
            cls.CAUTION = cls.FG_YELLOW
            cls.HIGHLIGHT1 = cls.FG_MAGENTA
            cls.HIGHLIGHT2 = cls.FG_CYAN
            cls.MATCH = cls.FG_BLUE
            cls.AMBIGUOUS = cls.FG_YELLOW
            cls.POSSIBLE = cls.FG_RED
            cls.RELATED = cls.FG_GREEN
            cls.DISCLOSED = cls.FG_MAGENTA
        # TODO
        # This class is mostly for sz_explorer as it has many color requirements
        # Other tools need to do basic coloring of text, setting this theme uses
        # the colors set by the terminal preferences so a user will see the colors
        # they expect in the output from tools
        elif theme.upper() == "TERMINAL":
            cls.GOOD = cls.FG_GREEN  # Green
            cls.BAD = cls.FG_RED  # Red
            cls.CAUTION = cls.FG_YELLOW  # Yellow
            cls.HIGHLIGHT1 = cls.FG_BLUE  # Blue
            cls.HIGHLIGHT2 = cls.FG_CYAN  # Cyan
            # TODO Add colors for the regex replace for colorizing json output
            cls.JSONKEYCOLOR = cls.FG_BLUE
            cls.JSONVALUECOLOR = cls.FG_YELLOW

    # Styles
    RESET = "\033[0m"
    BOLD = "\033[01m"
    DIM = "\033[02m"
    ITALICS = "\033[03m"
    UNDERLINE = "\033[04m"
    BLINK = "\033[05m"
    REVERSE = "\033[07m"
    STRIKETHROUGH = "\033[09m"
    INVISIBLE = "\033[08m"

    # Foregrounds
    FG_BLACK = "\033[30m"
    FG_WHITE = "\033[37m"
    FG_BLUE = "\033[34m"
    FG_MAGENTA = "\033[35m"
    FG_CYAN = "\033[36m"
    FG_YELLOW = "\033[33m"
    FG_GREEN = "\033[32m"
    FG_RED = "\033[31m"
    FG_LIGHTBLACK = "\033[90m"
    FG_LIGHTWHITE = "\033[97m"
    FG_LIGHTBLUE = "\033[94m"
    FG_LIGHTMAGENTA = "\033[95m"
    FG_LIGHTCYAN = "\033[96m"
    FG_LIGHTYELLOW = "\033[93m"
    FG_LIGHTGREEN = "\033[92m"
    FG_LIGHTRED = "\033[91m"

    # Backgrounds
    BG_BLACK = "\033[40m"
    BG_WHITE = "\033[107m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_YELLOW = "\033[43m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_LIGHTBLACK = "\033[100m"
    BG_LIGHTWHITE = "\033[47m"
    BG_LIGHTBLUE = "\033[104m"
    BG_LIGHTMAGENTA = "\033[105m"
    BG_LIGHTCYAN = "\033[106m"
    BG_LIGHTYELLOW = "\033[103m"
    BG_LIGHTGREEN = "\033[102m"
    BG_LIGHTRED = "\033[101m"

    # Extended
    FG_DARKORANGE = "\033[38;5;208m"
    FG_SYSTEMBLUE = "\033[38;5;12m"  # darker
    FG_DODGERBLUE2 = "\033[38;5;27m"  # lighter
    FG_PURPLE = "\033[38;5;93m"
    FG_DARKVIOLET = "\033[38;5;128m"
    FG_MAGENTA3 = "\033[38;5;164m"
    FG_GOLD3 = "\033[38;5;178m"
    FG_YELLOW1 = "\033[38;5;226m"
    FG_SKYBLUE1 = "\033[38;5;117m"
    FG_SKYBLUE2 = "\033[38;5;111m"
    FG_ROYALBLUE1 = "\033[38;5;63m"
    FG_CORNFLOWERBLUE = "\033[38;5;69m"
    FG_HOTPINK = "\033[38;5;206m"
    FG_DEEPPINK4 = "\033[38;5;89m"
    FG_SALMON = "\033[38;5;209m"
    FG_MEDIUMORCHID1 = "\033[38;5;207m"
    FG_NAVAJOWHITE3 = "\033[38;5;144m"
    FG_DARKGOLDENROD = "\033[38;5;136m"
    FG_STEELBLUE1 = "\033[38;5;81m"
    FG_GREY42 = "\033[38;5;242m"
    FG_INDIANRED = "\033[38;5;131m"
    FG_DEEPSKYBLUE1 = "\033[38;5;39m"
    FG_ORANGE3 = "\033[38;5;172m"
    FG_RED3 = "\033[38;5;124m"
    FG_SEAGREEN2 = "\033[38;5;83m"
    FG_SZRELATED = "\033[38;5;64m"
    FG_YELLOW3 = "\033[38;5;184m"
    FG_CYAN3 = "\033[38;5;43m"
    FG_CHARTREUSE3 = "\033[38;5;70m"
    FG_ORANGERED1 = "\033[38;5;202m"

    # Senzing
    SZ_BLUE = "\033[38;5;25m"
    SZ_LIGHTORANGE = "\033[38;5;172m"
    SZ_ORANGE = "\033[38;5;166m"
    SZ_GREEN = "\033[38;5;64m"
    SZ_PURPLE = "\033[38;5;93m"
    SZ_CYAN = "\033[38;5;68m"
    SZ_PINK = "\033[38;5;170m"
    SZ_RED = "\033[38;5;160m"
    SZ_YELLOW = "\033[38;5;178m"

    # TODO
    # Set the default theme colors initially
    TABLE_TITLE = FG_GREY42
    ROW_TITLE = FG_GREY42
    COLUMN_HEADER = FG_GREY42
    ENTITY_COLOR = SZ_PURPLE
    DSRC_COLOR = SZ_ORANGE
    ATTR_COLOR = SZ_BLUE
    GOOD = SZ_GREEN
    BAD = SZ_RED
    CAUTION = SZ_YELLOW
    HIGHLIGHT1 = SZ_PINK
    HIGHLIGHT2 = SZ_CYAN
    MATCH = SZ_BLUE
    AMBIGUOUS = SZ_LIGHTORANGE
    POSSIBLE = SZ_ORANGE
    RELATED = SZ_GREEN
    DISCLOSED = SZ_PURPLE
    # TODO Added
    JSONKEYCOLOR = FG_BLUE
    JSONVALUECOLOR = FG_YELLOW


# TODO Fully test
# -------------------------------------------------------------------------
# Engine configuration helper functions
# -------------------------------------------------------------------------


def check_environment() -> None:
    """# TODO"""
    # The Senzing python tools call G2Paths before starting engine to locate the engine configuration. Error if can't locate
    # a G2Module.ini or SENZING_ENGINE_CONFIGURATION_JSON
    if "SENZING_ETC_PATH" not in os.environ and "SENZING_ROOT" not in os.environ:
        # Check if set or not and that it's not set to null
        secj = os.environ.get("SENZING_ENGINE_CONFIGURATION_JSON")
        if not secj or (secj and len(secj) == 0):
            # TODO V4 doc links?
            print(
                textwrap.dedent(
                    """\n\
            ERROR: SENZING_ROOT or SENZING_ENGINE_CONFIGURATION_JSON environment variable is not set:

                - If using a Senzing project on a bare metal install, source the setupEnv file in the project root path.

                        https://senzing.zendesk.com/hc/en-us/articles/115002408867-Introduction-G2-Quickstart

                - If running within a container set the SENZING_ENGINE_CONFIGURATION_JSON environment variable.

                        https://github.com/Senzing/knowledge-base/blob/main/lists/environment-variables.md#senzing_engine_configuration_json
            """
                )
            )
            sys.exit(1)


# TODO Change to sz when changed in builds
def get_g2module_path() -> Path:
    """# TODO"""
    file_paths = []
    msg_args = f"Use command line argument -c (--inifile) to specify the path & filename for {CONFIG_FILE}\n"

    # Search paths checked for INI file requested. Path can be for a local Senzing project
    # (created with sz_create_project.py) or a 'system install' path - for example using an
    # asset from Senzing Git Hub mounting the path from the host into a container.

    # Get the path of the Senzing tools in case ini file is located there
    search_paths = [Path(sys.argv[0]).resolve().parent]

    # Senzing container assets set SENZING_ETC_PATH, check if set. This needs to be checked first
    if "SENZING_ETC_PATH" in os.environ:
        etc_path = os.environ.get("SENZING_ETC_PATH")
        if etc_path:
            search_paths.append(Path(etc_path))

    # SENZING_ROOT is set by a project setupEnv, append /etc where config file is expected
    if "SENZING_ROOT" in os.environ:
        root_path = os.environ.get("SENZING_ROOT")
        if root_path:
            search_paths.append(Path(root_path).joinpath("etc"))

    for path in search_paths:
        candidate_file = path.joinpath(CONFIG_FILE).resolve()
        if check_file_exists(candidate_file):
            file_paths.append(candidate_file)

    if len(file_paths) == 0:
        print(f"ERROR: {CONFIG_FILE} couldn't be located, searched: ")
        print_config_locations(search_paths)
        print(msg_args)
        sys.exit(1)

    if len(file_paths) > 1:
        print(f"ERROR: {CONFIG_FILE} found in multiple locations: ")
        print_config_locations(file_paths)
        print(msg_args)
        sys.exit(1)

    return file_paths[0]


def print_config_locations(locations: List[Path]) -> None:
    """# TODO"""
    _ = [print(f"\t{loc}") for loc in locations]
    print()


def get_ini_as_json_str(ini_file: Path) -> str:
    """Return a JSON string representation of an INI file."""
    # configparser doesn't throw an exception if file doesn't exist, test first
    try:
        with open(ini_file, encoding="utf-8") as test:
            _ = test.read()
    except IOError as err:
        raise err

    ini_parser = configparser.ConfigParser(
        empty_lines_in_values=False, interpolation=None
    )
    ini_parser.read(ini_file)
    config_dict: Dict[Any, Any] = {}

    for group_name in ini_parser.sections():
        normalized_group_name: str = group_name.upper()
        config_dict[normalized_group_name] = {}
        for var_name in ini_parser[group_name]:
            normalized_var_name: str = var_name.upper()
            config_dict[normalized_group_name][normalized_var_name] = ini_parser[
                group_name
            ][var_name]

    # Check ini file isn't empty
    if not config_dict:
        print(
            f"ERROR: Successfully read {ini_file} but it appears to be empty or malformed!"
        )
        sys.exit(0)

    return json.dumps(config_dict)


def get_engine_config(ini_file_name: Union[str, None] = None) -> str:
    """# TODO"""

    # Initial check to determine is environment variables expected are set
    check_environment()

    # If an ini file was passed in to a tool with -c (--iniFile) CLI argument
    if ini_file_name:
        return get_ini_as_json_str(Path(ini_file_name))

    # If ini file not passed in, look for engine config env var
    config_env_var = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
    if config_env_var:
        return config_env_var

    # If neither try and locate the ini file
    return get_ini_as_json_str(get_g2module_path())


# -------------------------------------------------------------------------
# File helper functions
# -------------------------------------------------------------------------


def check_file_exists(file_name: Union[Path, str]) -> bool:
    """# TODO"""

    if isinstance(file_name, str):
        file_name = Path(file_name)

    if not file_name.is_file():
        return False

    return True


# TODO Is this one needed still?s
# def check_file_readable(file_name: Union[Path, str]) -> bool:
#     """# TODO"""

#     if isinstance(file_name, str):
#         file_name = Path(file_name)

#     try:
#         _ = open(file_name, encoding="utf-8")
#     except PermissionError:
#         return False

#     return True


# -------------------------------------------------------------------------
# Color helper functions
# -------------------------------------------------------------------------


# TODO Is this needed with colorize_output?
# TODO colors_list is a string with multiple entries separated by ,
def colorize_str(string: str, colors_list: str = "") -> str:
    """# TODO"""

    return Colors.apply(string, colors_list)


def colorize_json(json_str: str) -> str:
    """# TODO"""
    key_replacer = rf"\1{Colors.JSONKEYCOLOR}\2{Colors.RESET}\3\4"
    value_replacer = rf"\1\2{Colors.JSONVALUECOLOR}\3{Colors.RESET}\4\5"
    # Look for values first to make regex a little easier to construct
    # Regex is matching: ': "Robert Smith", ' and using the groups in the replacer to add color
    json_color = re.sub(
        r"(: ?)(\")([\w\/+][^\{\"]+?)(\")(\}?|,{1}|\n)", value_replacer, json_str
    )
    # Regex is matching: ': "ENTITY_ID": ' and using the groups in the replacer to add color
    json_color = re.sub(r"(\")([\w ]*?)(\")(:{1})", key_replacer, json_color)

    return json_color


# TODO Used to color normal output messages
def colorize_output(
    # output: Union[int, str], color_or_type: str, output_color: bool = True
    output: Union[Exception, int, str],
    color_or_type: str,
) -> str:
    """# TODO"""

    # TODO Test tools work
    output = str(output) if isinstance(output, int) else output

    if not output:
        return ""

    # if output_color:
    #     return output

    color_or_type = color_or_type.upper()

    if color_or_type == "ERROR":
        output_type = "BAD"
    elif color_or_type == "WARNING":
        output_type = "CAUTION,ITALICS"
    elif color_or_type == "INFO":
        output_type = "HIGHLIGHT2"
    elif color_or_type == "SUCCESS":
        output_type = "GOOD"
    else:
        output_type = color_or_type

    return f"{Colors.apply(output, output_type)}"


# -------------------------------------------------------------------------
# Text output helper functions
# -------------------------------------------------------------------------


# TODO msg str can contain err in f-string
def print_error(msg: Union[Exception, str]) -> None:
    """# TODO"""
    print(colorize_output(f"\nERROR: {msg}\n", "error"))


# TODO msg str can contain err in f-string
def print_info(msg: Union[Exception, str]) -> None:
    """# TODO"""
    print(colorize_output(f"\n{msg}\n", "info"))


# TODO msg str can contain err in f-string
def print_warning(msg: Union[Exception, str]) -> None:
    """# TODO"""
    print(colorize_output(f"\nWARNING: {msg}\n", "warning"))


def print_response(
    response: Union[int, str],
    color_json: bool,
    color_json_cmd: bool,
    format_json: bool,
    format_json_cmd: bool,
    cmd_color: bool,
    cmd_format: bool,
    color: str = "",
) -> str:
    """# TODO"""
    strip_colors = True

    if not response:
        response = "No response!"
        color = "info"

    if isinstance(response, int):
        output = colorize_output(response, color)
    else:
        try:
            # Test if data is json and format appropriately
            _ = orjson.loads(response) if ORJSON_AVAIL else json.loads(response)
        except (JsonDecodeError, TypeError):
            output = colorize_output(response, color)
            strip_colors = False
        else:
            # TODO Is this check still needed?
            if type(response) not in [dict, list]:
                response = (
                    orjson.loads(response) if ORJSON_AVAIL else json.loads(response)
                )

            # Format JSON if global config or single command formatter specifies
            if (format_json and not cmd_format) or (cmd_format and format_json_cmd):
                json_ = (
                    orjson.dumps(response, option=orjson.OPT_INDENT_2)
                    if ORJSON_AVAIL
                    else json.dumps(response, indent=2)
                )
            else:
                json_: Union[bytes, str] = (  # type: ignore
                    orjson.dumps(response) if ORJSON_AVAIL else json.dumps(response)
                )

            json_str: str = json_.decode() if ORJSON_AVAIL else json_  # type: ignore

            # Color JSON if global config or single command formatter specifies
            if (color_json and not cmd_color) or (cmd_color and color_json_cmd):
                output = colorize_json(json_str)
            else:
                output = json_str

    print(f"\n{output}\n", flush=True)
    # Removing color codes, return output to set last_response for sending
    # to clipboard or file or reformatting JSON
    if strip_colors:
        return re.sub(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]", "", output)

    return output


# TODO Organise
# TODO Black formatting is off as it separates into multiple lines and the
# TODO pylint disable is ignored
# fmt: off
def do_shell(self: Union[SzCmdShell, SzCfgShell], line: str) -> None:  # pylint: disable=unused-argument
    """# TODO"""
    print(os.popen(line).read())
# fmt: on


def do_help(self: Union[SzCmdShell, SzCfgShell], help_topic: str) -> None:
    """# TODO"""
    if not help_topic or help_topic == "overview":
        self.help_overview()
        return

    if help_topic == "all":
        cmd.Cmd.do_help(self, "")
        return

    if help_topic not in self.get_names(include_hidden=True):
        help_topic = "do_" + help_topic
        # print(help_topic)
        # print(help_topic[3:])
        # print(self.get_names(include_hidden=True))
        if help_topic not in self.get_names(include_hidden=True):
            # cmd.Cmd.do_help(self, help_topic[3:])
            # do_help(self, help_topic[3:])
            print_warning(f"Command or help topic '{help_topic[3:]}' doesn't exist")
            return

    topic_docstring = getattr(self, help_topic).__doc__
    if not topic_docstring:
        print_warning(f"No help found for {help_topic[3:]}")
        return

    help_text = current_section = ""
    headers = [
        "Syntax:",
        "Examples:",
        "Example:",
        "Notes:",
        "Caution:",
        "Arguments:",
    ]

    help_lines = textwrap.dedent(topic_docstring).split("\n")

    for line in help_lines:
        line_color = ""
        if line:
            if line in headers:
                line_color = "highlight2"
                current_section = line

            if current_section == "Caution:":
                line_color = "caution, italics"

            if current_section not in (
                "Syntax:",
                "Examples:",
                "Example:",
                "Notes:",
                "Arguments:",
            ):
                line_color = ""

        if re.match(rf"^\s*{help_topic[3:]}", line) and not line_color:
            sep_column = line.find(help_topic[3:]) + len(help_topic[3:])
            help_text += (
                line[0:sep_column] + colorize_str(line[sep_column:], "dim") + "\n"
            )
        else:
            help_text += colorize_str(line, line_color) + "\n"

    print(help_text)


# def do_history(self: Union[SzCmdShell, SzCfgShell], arg) -> None:
def do_history(self: SzCmdShell, _: None) -> None:
    """# TODO"""

    if self.hist_avail:
        print()
        for i in range(readline.get_current_history_length()):
            print(readline.get_history_item(i + 1))
        print()
    else:
        self._print_response("History isn't available in this session.", "caution")
        # TODO Add report for hist_file_error


def history_setup(self: Union[SzCmdShell, SzCfgShell]) -> None:
    """Attempt to setup history file"""

    # TODO pathlib
    # tmp_hist = "." + os.path.basename(sys.argv[0].lower().replace(".py", "_history"))

    # # TODO
    base_name = "." + Path(sys.argv[0]).stem + "_history"
    self.hist_file_name = Path.home().joinpath(base_name)

    # self.hist_file_name = os.path.join(os.path.expanduser("~"), tmp_hist)

    # Try and open history in users home first for longevity
    try:
        with open(self.hist_file_name, "a", encoding="utf-8"):
            pass
    except IOError as err:
        # TODO Only use /tmp in a container for security
        self.hist_file_error = f"{err} - Couldn't use home, trying /tmp/..."
        self.hist_file_name = f"/tmp/{tmp_hist}"
        self.hist_file_name = Path("/tmp").joinpath(base_name)
        # Can't use users home, try using /tmp/ for history useful at least in the session
        try:
            with open(self.hist_file_name, "a", encoding="utf-8"):
                pass
        except IOError as err2:
            self.hist_file_error = f"{err2} - User home dir and /tmp/ failed!"
            return

    hist_size = 2000
    readline.read_history_file(self.hist_file_name)
    readline.set_history_length(hist_size)
    # TODO Is using atexit a good idea here? Do after each command instead?
    atexit.register(readline.set_history_length, hist_size)
    atexit.register(readline.write_history_file, self.hist_file_name)

    self.hist_file_error = None
    self.hist_avail = True


def do_responseToClipboard(self, _) -> None:  # type: ignore[no-untyped-def]
    """# TODO"""
    # TODO Test new lines around output
    if not PYCLIP_AVAIL:
        print_info(
            textwrap.dedent(
                """
                    - To send the last response to the clipboard the Python module pyclip needs to be installed
                        - pip install pyclip
                """
            )
        )
        return

    try:
        _ = pyclip.detect_clipboard()
    except ClipboardSetupException as err:
        print_warning(f"Problem detecting clipboard: {err}")
        return

    # TODO Try and break this to see if needs try/except
    try:
        pyclip.copy(self.last_response)
    except pyclip.base.ClipboardException as err:
        print_warning(f"Couldn't copy to clipboard: {err}")


def do_responseToFile(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """# TODO"""
    try:
        with open(kwargs["parsed_args"].file_path, "w", encoding="utf-8") as out:
            out.write(self.last_response)
            out.write("\n")
    except IOError as err:
        print_error(err)


# TODO args? kwargs??
# TODO Doesn't put the reformat in last_response, should it
def do_responseReformatJson(
    last_response: str, color_json: bool, format_json: bool
) -> None:
    """# TODO"""
    try:
        # TODO Orjson?
        _ = json.loads(last_response)
    # TODO Correct JSONDecodeError?
    except (json.decoder.JSONDecodeError, TypeError):
        print_warning("The last response isn't JSON")
        return

    print_response(last_response, color_json, False, not format_json, False, False)