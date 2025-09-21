"""Legacy placeholder (server_copy_tmp)

Implementation removed. Do NOT import. Use backend.server and
backend.db_utils.db_conn instead. This stub will be deleted soon.
"""

from __future__ import annotations

__all__ = ["_connect_db"]

def _connect_db():  # pragma: no cover
    raise RuntimeError(
        (
            "server_copy_tmp._connect_db() removed. Use backend.server + "
            "backend.db_utils.db_conn."
        )
    )

# File intentionally truncated.
