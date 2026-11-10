"""Private filesystem setup for SQLite stores containing owner data."""
from __future__ import annotations

import os
from pathlib import Path


def prepare_private_sqlite(path: Path) -> Path:
    """Create/secure a SQLite path before SQLite opens it; refuse symlink targets."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    if path.is_symlink():
        raise OSError("Refusing a symlink for a private SQLite database.")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        if not path.is_file():
            raise OSError("Private SQLite path is not a regular file.")
        os.chmod(path, 0o600)
    else:
        os.close(fd)
    return path
