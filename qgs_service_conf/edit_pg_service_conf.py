"""
Module to locate, read, edit, and persist pg_service.conf in the user directory.
"""

import platform
import os
import shutil
from pathlib import Path
from configparser import ConfigParser, MissingSectionHeaderError
from typing import Dict, Any

def os_is_windows() -> bool:
    """Return True if running on Windows."""
    return platform.system().lower() == "windows"

def path_to_conf(is_windows: bool) -> Path:
    """
    Return the expanded Path to pg_service.conf based on OS.

    On Windows: uses %APPDATA%\\postgresql\\.pg_service.conf
    On POSIX: uses ~/.pg_service.conf
    """
    if is_windows:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable is not set on Windows.")
        psc_path = Path(appdata) / "postgresql" / ".pg_service.conf"
    else:
        psc_path = Path.home() / ".pg_service.conf"
    return psc_path.expanduser()

def read_service_conf(path_to_psc: Path) -> Dict[str, Dict[str, str]]:
    """
    Read the pg_service.conf and return its contents as a nested dict.
    Creates an empty file if it doesn't exist.

    :param path_to_psc: Path to pg_service.conf
    """
    if not path_to_psc.exists():
        # ensure parent exists (especially on Windows)
        path_to_psc.parent.mkdir(parents=True, exist_ok=True)
        path_to_psc.write_text("", encoding="utf-8")
        print(f"{path_to_psc!s} not found. Created empty file.")

    parser = ConfigParser()
    try:
        parser.read(path_to_psc, encoding="utf-8")
    except MissingSectionHeaderError as e:
        raise ValueError(f"Configuration file at {path_to_psc!s} is malformed: {e}") from e

    return {section: dict(parser[section]) for section in parser.sections()}

def write_service_conf(path_to_psc: Path, services: Dict[str, Dict[str, Any]], make_backup: bool = True) -> None:
    """
    Writes the services dict to .pg_service.conf, with optional backup.

    :param path_to_psc: Path to .pg_service.conf.
    :param services: Dictionary of service sections to write.
    :param make_backup: If True, preserve existing file as .bak before overwriting.
    """
    if make_backup and path_to_psc.exists():
        backup = path_to_psc.with_suffix(path_to_psc.suffix + ".bak")
        shutil.copy2(path_to_psc, backup)

    parser = ConfigParser()
    for section, opts in services.items():
        parser[section] = {k: str(v) for k, v in opts.items()}

    # Ensure parent directory exists
    path_to_psc.parent.mkdir(parents=True, exist_ok=True)
    with open(path_to_psc, "w", encoding="utf-8") as f:
        parser.write(f)

def edit_service(services: Dict[str, Dict[str, Any]], service: str, params: Dict[str, Any]) -> None:
    """
    Add or update a service entry in the services dict.

    :param services: Existing services dict (will be mutated).
    :param service: Name of the service section to add/edit.
    :param params: Dict of parameters (e.g., host, port, dbname, user, password).
    """
    services[service] = {k: str(v) for k, v in params.items()}
    print(f"Service '{service}' updated/added.")

def redact_sensitive(cfg: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of cfg with password redacted for safe display."""
    redacted = cfg.copy()
    if "password" in redacted:
        redacted["password"] = "*****"
    return redacted

def normalize_entry(entry: Dict[str, str]) -> Dict[str, Any]:
    """Coerce known types (e.g., port to int)."""
    normalized = entry.copy()
    if "port" in normalized:
        try:
            normalized["port"] = int(normalized["port"])
        except ValueError:
            pass  # leave as string if not integer
    return normalized

def delete_service(services: dict, service: str) -> None:
    """
    Deletes service from services-dict.

    :param services: Existing services-dict.
    :param service: Name of service to be deleted.
    :raises KeyError: If service does not exist.
    """
    if service not in services:
        raise KeyError(f"Service '{service}' does not exist and can not be deleted.")
    del services[service]
    print(f"Service '{service}' deleted.")

def create_service(services: dict, service: str, params: dict, overwrite: bool = False) -> None:
    """
    Create a new service entry. Raises if it already exists unless overwrite=True.

    :param services: Existing services dict (will be mutated).
    :param service: Name of the new service section.
    :param params: Dict of parameters (must include at least host, port, dbname, user).
                   Password is optional but typical.
    :param overwrite: If True, will replace an existing service silently.
    :raises ValueError: If required fields are missing or service exists without overwrite.
    """
    required = {"host", "port", "dbname", "user"}
    missing = required - set(params.keys())
    if missing:
        raise ValueError(f"Missing required fields for service '{service}': {', '.join(sorted(missing))}")

    if service in services and not overwrite:
        raise ValueError(f"Service '{service}' already exists. Use overwrite=True to replace it.")

    # Normalize all values to strings
    services[service] = {k: str(v) for k, v in params.items()}
    print(f"Service '{service}' {'created' if service not in services or overwrite else 'added'}.")
