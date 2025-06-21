"""Helpers for creating and updating projects"""

import json
import operator
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

V3_BACKUP_PATH = "v3_to_v4_upgrade_backups"
V4_BUILD = "szBuildVersion.json"
SZ_SYS_PATH = Path("/opt/senzing")
V4_SYS_PATH = SZ_SYS_PATH / "er"
V4_DATA_PATH = SZ_SYS_PATH / "data"
V4_SYS_BUILD = V4_SYS_PATH / V4_BUILD

COPY_TO_PROJ = {
    "er/": {"files": ["*"], "excludes": ["sz_create_project", "sz_update_project", "_project_helpers.py"]},
    "data": {"files": ["*"], "excludes": []},
}

PERMISSIONS = {
    ".": {
        "dir_pint": 0,
        "file_pint": 0o660,
        "files": ["LICENSE", "NOTICES", "README.1ST", "szBuildVersion.json"],
        "excludes": ["setupEnv"],
        "recursive": False,
    },
    "setupEnv": {"dir_pint": 0, "file_pint": 0o770, "files": [], "excludes": [], "recursive": False},
    "bin": {
        "dir_pint": 0o770,
        "file_pint": 0o770,
        "files": ["*"],
        "excludes": ["__pycache__", "_sz_database.py", "_tool_helpers.py"],
        "recursive": False,
    },
    "data": {"dir_pint": 0o770, "file_pint": 0o660, "files": ["*"], "excludes": [], "recursive": True},
    "lib": {"dir_pint": 0o770, "file_pint": 0o660, "files": ["*"], "excludes": [], "recursive": False},
    "resources": {"dir_pint": 0o770, "file_pint": 0o660, "files": ["*"], "excludes": ["setupEnv"], "recursive": True},
    "resources/templates/setupEnv": {
        "dir_pint": 0,
        "file_pint": 0o770,
        "files": [],
        "excludes": [],
        "recursive": False,
    },
    "sdk": {"dir_pint": 0o770, "file_pint": 0o660, "files": ["*"], "excludes": [], "recursive": True},
    V3_BACKUP_PATH: {"dir_pint": 0o770, "file_pint": 0, "files": [], "excludes": [], "recursive": False},
}

PERMISSIONS_2 = {
    "bin": {
        "dir_pint": 0o770,
        "file_pint": 0o660,
        "files": ["_sz_database.py", "_tool_helpers.py"],
        "excludes": [],
        "recursive": False,
    }
}


@dataclass()
class SzBuildDetails:
    """
    Build information for a project or Senzing SDK system install
    SzBuildDetails(platform='Linux', version='4.0.0', build_version='4.0.0.25164', build_number='2025_06_13__13_07', major=4, minor=0, micro=0)
    """

    platform: str
    version: str
    build_version: str
    build_number: str
    major: int = field(init=False)
    minor: int = field(init=False)
    micro: int = field(init=False)
    build_v: int = field(init=False)

    def __post_init__(self) -> None:
        self.major, self.minor, self.micro, self.build_v = [int(n) for n in self.build_version.split(".")]

    def _operators(self, other: "SzBuildDetails", operator_: Any) -> tuple[bool, ...]:
        """Check instances of version details are with different operators"""
        to_compare = (
            (self.major, other.major),
            (self.minor, other.minor),
            (self.micro, other.micro),
            (self.build_v, other.build_v),
        )
        return tuple(operator_(t[0], t[1]) for t in to_compare)

    def __lt__(self, other: "SzBuildDetails") -> bool:
        if not isinstance(other, SzBuildDetails):
            return NotImplemented

        major_equal, minor_equal, micro_equal, _ = self._operators(other, operator.eq)
        major_lt, minor_lt, micro_lt, build_v_lt = self._operators(other, operator.lt)

        if major_lt or (
            major_equal and any((minor_lt, all((minor_equal, micro_lt)), all((minor_equal, micro_equal, build_v_lt))))
        ):
            return True

        return False

    def __gt__(self, other: "SzBuildDetails") -> bool:
        if not isinstance(other, SzBuildDetails):
            return NotImplemented

        major_equal, minor_equal, micro_equal, _ = self._operators(other, operator.eq)
        major_gt, minor_gt, micro_gt, build_v_gt = self._operators(other, operator.gt)

        if major_gt or (
            major_equal and any((minor_gt, all((minor_equal, micro_gt)), all((minor_equal, micro_equal, build_v_gt))))
        ):
            return True

        return False


def get_build_details(path: Path) -> SzBuildDetails:
    """Return dataclass with the details from a build file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            # Ignore DATA_VERSION, V3 build files had it V4 doesn't
            version_dict = {k.lower(): v for k, v in json.load(f).items() if k != "DATA_VERSION"}
    except (OSError, json.JSONDecodeError) as err:
        raise OSError(f"Couldn't get the build information from {path}: {err}") from err

    return SzBuildDetails(**version_dict)


def copy_files_dirs(to_copy: dict[str, Any], source_dir: Path, target_dir: Path) -> None:
    """Copy files/directories within and to a project"""
    for c_path, c_dict in to_copy.items():
        excludes = c_dict["excludes"]
        files = c_dict["files"]
        source = source_dir / c_path

        try:
            if source.is_dir():
                # If the key in to_copy ends with / copy everything in source dir to target_dir
                #     er/ as the key copies everything from /opt/senzing/er to target_dir
                #
                # If the key in to_copy doesn't end with / copy source dir and everything in it to target_dir
                #     data as the key copies /opt/senzing/data to target_dir/data
                target = target_dir if c_path.endswith("/") else target_dir / c_path

                # Copy entire contents of the source directory
                if not files or (files and files[0] == "*"):
                    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*excludes), dirs_exist_ok=True)

                # Create the source directory in the target and only copy listed files
                if files and files[0] != "*":
                    target.mkdir(exist_ok=True, parents=True)
                    for source_file in [source / f for f in files]:
                        shutil.copy(source_file, target / source_file.name)

            if source.is_file():
                # Single file copy always copies only the file, if the key to to_copy is er/szBuildVersion.json
                # szBuildVersion.json is copied to target_dir and not target_dir/er/szBuildVersion.json
                target = target_dir / source.name
                target_dir.mkdir(exist_ok=True, parents=True)
                shutil.copy(source, target)
        except OSError as err:
            raise OSError(f"Couldn't copy a file or directory: {err}") from err


def setup_env(proj_path: Path) -> None:
    """Create a new setupEnv and replace place holders with paths for the project"""
    try:
        shutil.copy(proj_path / "resources/templates/setupEnv", proj_path)
        setup_path = proj_path / "setupEnv"

        with open(setup_path, "r", encoding="utf-8") as in_:
            data = in_.read()

        data = data.replace("${SENZING_DIR}", str(proj_path)).replace("${SENZING_CONFIG_PATH}", str(proj_path / "etc"))

        with open(setup_path, "w", encoding="utf-8") as out:
            out.write(data)
    except OSError as err:
        raise OSError(f"Couldn't create a new setupEnv file: {err}") from err


def set_permissions(proj_path: Path, permissions: dict[str, dict[str, Any]]) -> None:
    """Set permissions for files/dirs copied to the project, or dirs removed and replaced completely e.g., data/"""
    try:
        for p_path, p_dict in permissions.items():
            dir_pint = p_dict["dir_pint"]
            file_pint = p_dict["file_pint"]
            files = p_dict["files"]
            recursive = p_dict["recursive"]
            target = proj_path if p_path.startswith(".") else proj_path / p_path
            excludes = [target / e for e in p_dict["excludes"]]

            if target.is_dir():
                if dir_pint != 0:
                    target.chmod(dir_pint)
                    d_chmods = (
                        [d for d in target.glob("*") if d.is_dir() and not d.is_symlink() and d not in excludes]
                        if not recursive
                        else [d for d in target.rglob("*") if d.is_dir() and not d.is_symlink() and d not in excludes]
                    )
                    for dir_ in d_chmods:
                        dir_.chmod(dir_pint)

                if files and files[0] == "*":
                    f_chmods = (
                        [f for f in target.glob("*") if f.is_file() and not f.is_symlink() and f not in excludes]
                        if not recursive
                        else [f for f in target.rglob("*") if f.is_file() and not f.is_symlink() and f not in excludes]
                    )

                    for file in f_chmods:
                        Path(target / file).chmod(file_pint)

                if files and files[0] != "*":
                    for file in files:
                        Path(target / file).chmod(file_pint)

            if target.is_file():
                target.chmod(file_pint)
    except OSError as err:
        raise OSError(f"Couldn't set a permission: {err}") from err
