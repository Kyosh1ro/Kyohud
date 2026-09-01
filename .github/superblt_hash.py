"""Compute SuperBLT-compatible file and directory hashes.

This is an independent implementation of the hashing scheme documented by
SuperBLT and the previous release tool. It uses only the Python standard
library and is regression-tested against the former `hash.exe` outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


BLOCK_SIZE = 8192


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(BLOCK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def hash_file(path: Path) -> str:
    """Return the SuperBLT hash for one file."""
    return _sha256_text(_sha256_file(path))


def hash_directory(path: Path) -> str:
    """Return the SuperBLT hash for every file below a directory."""
    ordered_hashes = []
    for file_path in path.rglob("*"):
        if file_path.is_file():
            sort_key = str(file_path).lower().encode("utf-8")
            ordered_hashes.append((sort_key, _sha256_file(file_path)))

    ordered_hashes.sort(key=lambda item: item[0])
    return _sha256_text("".join(file_hash for _, file_hash in ordered_hashes))


def hash_path(path: Path) -> str:
    if path.is_dir():
        return hash_directory(path)
    if path.is_file():
        return hash_file(path)
    raise FileNotFoundError(f"Path does not exist: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute a SuperBLT-compatible file or directory hash."
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    try:
        result = hash_path(args.path)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
