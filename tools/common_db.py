#!/usr/bin/env python3
"""
Funciones utilitarias para resolver y normalizar la ruta de la BD canónica
`chipax_data.db` de forma coherente entre herramientas.

Convenciones:
- Permite sobreescribir con la variable de entorno `DB_PATH`.
- Por defecto se usa SIEMPRE la ruta dentro del proyecto:
  `data/chipax_data.db`.
- Alternativa opcional (solo si se fuerza): el raíz del workspace
  (p. ej. `c:\\Odoo\\custom_addons\\chipax_data.db`).
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Devuelve la carpeta raíz del repo (ofitec.ai).

    Asume que este archivo vive en `tools/` dentro del repo.
    """
    return Path(__file__).resolve().parents[1]


def workspace_root() -> Path:
    """Devuelve el directorio raíz del workspace (padre del repo)."""
    return repo_root().parent


def default_db_path(prefer_root: bool = False) -> str:
    """Resuelve la ruta por defecto de la BD.

    Orden de preferencia:
    1) `DB_PATH` si está definido
    2) Si `prefer_root=True`: `<workspace_root>/chipax_data.db`
       Si `prefer_root=False`: `<repo_root>/data/chipax_data.db`
    """
    env = os.environ.get("DB_PATH")
    if env:
        return str(Path(env).resolve())

    if prefer_root:
        return str((workspace_root() / "chipax_data.db").resolve())
    return str((repo_root() / "data" / "chipax_data.db").resolve())


def existing_db_path() -> str | None:
    """Devuelve una ruta existente a la BD si se encuentra en ubicaciones conocidas."""
    env = os.environ.get("DB_PATH")
    if env and Path(env).exists():
        return str(Path(env).resolve())

    data_db = repo_root() / "data" / "chipax_data.db"
    if data_db.exists():
        return str(data_db.resolve())

    root_db = workspace_root() / "chipax_data.db"
    if root_db.exists():
        return str(root_db.resolve())

    return None


def ensure_parent_dir(path: str) -> None:
    """Crea el directorio padre si no existe (idempotente)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
