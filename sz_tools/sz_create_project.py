#! /usr/bin/env python3

""" # TODO """

import argparse
import json
import sys
from pathlib import Path
from shutil import copyfile, copytree, ignore_patterns
from typing import List, Union

# Metadata

__version__ = "0.0.1"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = "2024-06-13"
__updated__ = "2024-06-13"


def get_version_details(sz_root_path: Path) -> List[str]:
    """Return version details of Senzing installation"""
    try:
        sz_root_path = sz_root_path.joinpath("g2BuildVersion.json")
        with open(sz_root_path, encoding="utf-8") as file_version:
            version_details = json.load(file_version)
    except IOError as err:
        # TODO print_error() when have helpers?
        print(
            f"\nERROR: Unable to read {sz_root_path} to retrieve version details - {err}"
        )
        sys.exit(1)
    # TODO test with dodgy input file
    except json.JSONDecodeError as err:
        print(f"\nERROR: {err}")

    details: List[str] = []
    details.append(version_details.get("BUILD_VERSION", ""))
    details.append(version_details.get("DATA_VERSION", ""))

    if not all(details):
        # TODO print_error() or warning when have helpers?
        print(
            f"\nERROR: Problem reading values from version details, missing value(s) - {details}"
        )
        sys.exit(1)

    return details


def replace_in_file(filename: Path, old_string: str, new_string: str) -> None:
    """Replace strings in new project files"""

    try:
        with open(filename, encoding="utf-8") as fr:
            data = fr.read()
        with open(filename, "w", encoding="utf-8") as fw:
            fw.write(data.replace(old_string, new_string))
    except IOError as err:
        raise err


def set_folder_permissions(
    path: Path, permissions: int, folders_to_ignore: Union[List[str], None] = None
) -> None:
    """Set permissions recursively on a folder, optionally ignore specific folders"""
    if folders_to_ignore is None:
        folders_to_ignore = []

    path.chmod(permissions)

    dirs: List[Path] = [
        d
        for d in path.rglob("*")
        if d.is_dir() and not d.is_symlink() and d not in folders_to_ignore
    ]
    for dir_ in dirs:
        dir_.chmod(permissions)


def set_file_permissions(
    path: Path,
    permissions: int,
    files_to_ignore: Union[List[str], None] = None,
    recursive: bool = False,
) -> None:
    """Set permissions on files in a folder, optionally do recursively"""
    if files_to_ignore is None:
        files_to_ignore = []

    files: List[Path] = []
    if recursive:
        files = [f for f in path.rglob("*") if f.is_file() and f not in files_to_ignore]
    else:
        files = [f for f in path.iterdir() if f.is_file() and f not in files_to_ignore]

    for file in files:
        file.chmod(permissions)


def main() -> None:
    """main"""
    parser = argparse.ArgumentParser(
        description="Create a new instance of a Senzing project in a path"
    )
    parser.add_argument(
        "path",
        default="~/senzing",
        help="path to create new Senzing project in, it must not already exist (Default: %(default)s)",
        metavar="PATH",
        nargs="?",
    )
    args = parser.parse_args()

    # sz_path on normal rpm/deb install = /opt/senzing/g2
    # sz_install_root would then = /opt/senzing
    # TODO Put back when in API package
    # sz_path = Path(__file__).resolve().parents[1]
    sz_path = Path("/opt/senzing/g2").resolve()
    sz_path_root = Path(__file__).resolve().parents[2]
    project_path = Path(args.path).expanduser().resolve()

    bin_path = project_path.joinpath("bin")
    data_path = project_path.joinpath("data")
    etc_path = project_path.joinpath("etc")
    lib_path = project_path.joinpath("lib")
    python_path = project_path.joinpath("python")
    resources_path = project_path.joinpath("resources")
    sdk_path = project_path.joinpath("sdk")
    var_path = project_path.joinpath("var")

    if project_path.exists() and project_path.samefile(sz_path_root):
        print(
            f"\nProject cannot be created in {sz_path_root}. Please specify a different path."
        )
        sys.exit(1)

    if project_path.exists():
        print(f"\n{project_path} exists, please specify a different path.")
        sys.exit(1)

    version_details = get_version_details(sz_path)
    print(
        (
            f"\nProject location: {project_path}\n"
            f"Senzing version:  {version_details[0]}\n"
            f"Data version:     {version_details[1]}\n"
        )
    )

    # TODO Change names when tools updated
    ignore_files = ["G2CreateProject.py", "G2UpdateProject.py"]
    # Example: ignore_paths = [sz_path.joinpath('python')]
    ignore_paths: List[str] = []
    excludes = ignore_files + ignore_paths

    # Copy sz_path to new project path
    copytree(sz_path, project_path, ignore=ignore_patterns(*excludes), symlinks=True)

    # Copy resources/templates to etc
    ignore_files = ["G2C.db", "setupEnv", "*.template", "g2config.json"]
    copytree(
        sz_path.joinpath("resources", "templates"),
        etc_path,
        ignore=ignore_patterns(*ignore_files),
    )

    # Copy setupEnv
    copyfile(
        sz_path.joinpath("resources", "templates", "setupEnv"),
        project_path.joinpath("setupEnv"),
    )

    # Copy G2C.db to runtime location
    Path.mkdir(project_path.joinpath("var", "sqlite"), parents=True)
    copyfile(
        sz_path.joinpath("resources", "templates", "G2C.db"),
        var_path.joinpath("sqlite", "G2C.db"),
    )

    # Soft link data
    data_path.symlink_to(sz_path_root.joinpath("data", version_details[1]))

    # Files & strings to modify
    update_files = [
        project_path.joinpath("setupEnv"),
        etc_path.joinpath("G2Module.ini"),
    ]

    path_subs = [
        ("${SENZING_DIR}", project_path),
        ("${SENZING_CONFIG_PATH}", etc_path),
        ("${SENZING_DATA_DIR}", data_path),
        ("${SENZING_RESOURCES_DIR}", resources_path),
        ("${SENZING_VAR_DIR}", var_path),
    ]

    for file in update_files:
        for path in path_subs:
            replace_in_file(file, path[0], str(path[1]))

    # Folder permissions
    set_folder_permissions(project_path, 0o770)

    # Root of project
    set_file_permissions(project_path, 0o660)
    project_path.joinpath("setupEnv").chmod(0o770)

    # bin
    set_file_permissions(bin_path, 0o770)

    # etc
    set_file_permissions(etc_path, 0o660)

    # lib
    set_file_permissions(
        lib_path,
        0o660,
        files_to_ignore=["g2.jar"],
    )
    lib_path.joinpath("g2.jar").chmod(0o664)

    # python
    set_file_permissions(python_path, 0o660, recursive=True)
    python_path.joinpath("G2Audit.py").chmod(0o770)
    python_path.joinpath("G2Command.py").chmod(0o770)
    python_path.joinpath("G2ConfigTool.py").chmod(0o770)
    python_path.joinpath("G2Database.py").chmod(0o770)
    python_path.joinpath("G2Explorer.py").chmod(0o770)
    python_path.joinpath("G2Export.py").chmod(0o770)
    python_path.joinpath("G2Loader.py").chmod(0o770)
    python_path.joinpath("G2SetupConfig.py").chmod(0o770)
    python_path.joinpath("G2Snapshot.py").chmod(0o770)
    python_path.joinpath("demo", "truth", "truthset-load1.sh").chmod(0o770)
    python_path.joinpath("demo", "truth", "truthset-load2.sh").chmod(0o770)
    python_path.joinpath("demo", "truth", "truthset-load3.sh").chmod(0o770)

    # resources
    set_file_permissions(resources_path, 0o660, recursive=True)
    resources_path.joinpath("templates", "setupEnv").chmod(0o770)

    # sdk
    set_file_permissions(sdk_path, 0o664, recursive=True)

    # var
    set_file_permissions(var_path, 0o660, recursive=True)

    print("Successfully created.")


if __name__ == "__main__":
    main()