import os
import shutil
import platform
import tempfile
from pathlib import Path
from configparser import ConfigParser, MissingSectionHeaderError
from typing import Dict, Any

def os_is_windows() -> bool:
    return platform.system().lower() == "windows"

def path_to_conf(is_windows: bool) -> Path:
    if is_windows:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable is not set on Windows.")
        psc_path = Path(appdata) / "postgresql" / ".pg_service.conf"
    else:
        psc_path = Path.home() / ".pg_service.conf"
    return psc_path.expanduser()

def read_service_conf(path_to_psc: Path) -> Dict[str, Dict[str, str]]:
    if not path_to_psc.exists():
        path_to_psc.parent.mkdir(parents=True, exist_ok=True)
        path_to_psc.write_text("", encoding="utf-8")
    parser = ConfigParser()
    try:
        parser.read(path_to_psc, encoding="utf-8")
    except MissingSectionHeaderError as e:
        raise ValueError(f"Malformed config: {e}") from e
    return {section: dict(parser[section]) for section in parser.sections()}

def write_service_conf(path_to_psc: Path, services: Dict[str, Dict[str, Any]], make_backup: bool = True) -> None:
    """
    Schreibt eine .pg_service.conf mit exakt der Form key=value (ohne Leerzeichen).
    Macht optional ein Backup der bestehenden Datei und schreibt atomar.
    """
    if make_backup and path_to_psc.exists():
        backup = path_to_psc.with_suffix(path_to_psc.suffix + ".bak")
        shutil.copy2(path_to_psc, backup)

    path_to_psc.parent.mkdir(parents=True, exist_ok=True)

    dir_for_temp = path_to_psc.parent
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=dir_for_temp) as tmp:
        for service_name, params in services.items():
            tmp.write(f"[{service_name}]\n")
            for key, value in params.items():
                tmp.write(f"{key}={value}\n")
            tmp.write("\n")
        temp_name = tmp.name

    try:
        os.chmod(temp_name, 0o600)
    except Exception:
        pass  

    os.replace(temp_name, path_to_psc)

def create_service(services: Dict[str, Dict[str, Any]], service: str, params: Dict[str, Any], overwrite: bool = False) -> None:
    required = {"host", "port", "dbname", "user"}
    missing = required - set(params.keys())
    if missing:
        raise ValueError(f"Fehlende Felder für Service '{service}': {', '.join(sorted(missing))}")
    if service in services and not overwrite:
        raise ValueError(f"Service '{service}' existiert bereits. Mit overwrite=True überschreiben.")
    services[service] = {k: str(v) for k, v in params.items()}

def edit_service(services: Dict[str, Dict[str, Any]], service: str, params: Dict[str, Any]) -> None:
    if service not in services:
        raise KeyError(f"Service '{service}' existiert nicht zum Bearbeiten.")
    services[service] = {k: str(v) for k, v in params.items()}

def delete_service(services: Dict[str, Dict[str, Any]], service: str) -> None:
    if service not in services:
        raise KeyError(f"Service '{service}' existiert nicht zum Löschen.")
    del services[service]

def redact_sensitive(cfg: Dict[str, str]) -> Dict[str, str]:
    redacted = cfg.copy()
    if "password" in redacted:
        redacted["password"] = "*****"
    return redacted
