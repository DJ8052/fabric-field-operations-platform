"""Validate source-like operational CSVs and copy them unchanged to Bronze."""

from __future__ import annotations

import csv
import io
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from .entity_config import ENTITY_CONFIGS, EntityConfig, get_entity_config

DEFAULT_BRONZE_ROOT = "Files/bronze/operations"
DEFAULT_MAX_SOURCE_BYTES = 64 * 1024 * 1024
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class IngestionError(RuntimeError):
    """Raised when an operational source cannot be safely ingested."""


@dataclass(frozen=True)
class IngestionResult:
    entity_name: str
    source_path: str
    destination_path: str
    row_count: int


def _date_text(value: date | str) -> str:
    try:
        parsed = value if isinstance(value, date) else date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise IngestionError("ingestion_date must be a date or ISO date string") from exc
    return parsed.isoformat()


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise IngestionError("run_id must contain only letters, numbers, dot, underscore, or hyphen")
    return run_id


def build_destination_path(config: EntityConfig, ingestion_date: date | str, run_id: str, bronze_root: str = DEFAULT_BRONZE_ROOT) -> str:
    """Build the stable partitioned CSV destination path."""
    if not isinstance(bronze_root, str) or not bronze_root.strip():
        raise IngestionError("bronze_root must be a non-empty string")
    return str(PurePosixPath(bronze_root.strip()) / config.folder / f"ingestion_date={_date_text(ingestion_date)}" / f"run_{_validate_run_id(run_id)}.csv")


def _validate_local_csv(source: Path, config: EntityConfig) -> int:
    if not source.is_file():
        raise IngestionError(f"Source CSV does not exist: {source}")
    try:
        with source.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = tuple(reader.fieldnames or ())
            missing = [column for column in config.required_columns if column not in columns]
            if missing:
                raise IngestionError(f"{config.name} source is missing required columns: {', '.join(missing)}")
            row_count = sum(1 for _ in reader)
    except UnicodeDecodeError as exc:
        raise IngestionError(f"Source CSV must be UTF-8: {source}") from exc
    if row_count == 0:
        raise IngestionError(f"{config.name} source CSV contains no data rows")
    return row_count


def _validate_csv_text(
    content: str,
    source_path: str,
    config: EntityConfig,
) -> int:
    """Validate UTF-8 CSV text using the standard library."""
    try:
        reader = csv.DictReader(io.StringIO(content, newline=""))
        columns = tuple(reader.fieldnames or ())
        missing = [
            column
            for column in config.required_columns
            if column not in columns
        ]
        if missing:
            raise IngestionError(
                f"{config.name} source is missing required columns: "
                f"{', '.join(missing)}"
            )
        row_count = sum(1 for _ in reader)
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(
            f"Unable to parse {config.name} source CSV: {source_path}"
        ) from exc
    if row_count == 0:
        raise IngestionError(f"{config.name} source CSV contains no data rows")
    return row_count


def _validate_with_filesystem(
    filesystem: Any,
    source_path: str,
    config: EntityConfig,
    max_source_bytes: int,
) -> int:
    """Read and validate a Fabric file without starting Spark."""
    if (
        not isinstance(max_source_bytes, int)
        or isinstance(max_source_bytes, bool)
        or max_source_bytes <= 0
    ):
        raise IngestionError("max_source_bytes must be a positive integer")
    try:
        content = filesystem.head(source_path, max_source_bytes)
    except Exception as exc:
        raise IngestionError(
            f"Unable to read {config.name} source CSV: {source_path}"
        ) from exc
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IngestionError(
                f"Source CSV must be UTF-8: {source_path}"
            ) from exc
    if not isinstance(content, str):
        raise IngestionError(
            "filesystem.head must return source content as text or bytes"
        )
    if len(content.encode("utf-8")) >= max_source_bytes:
        raise IngestionError(
            f"{config.name} source reached the {max_source_bytes}-byte "
            "validation limit; increase max_source_bytes"
        )
    return _validate_csv_text(content, source_path, config)


def ingest_entity(entity_name: str, source_path: str | Path, ingestion_date: date | str, run_id: str, *, bronze_root: str = DEFAULT_BRONZE_ROOT, filesystem: Any | None = None, spark: Any | None = None, overwrite: bool = False, max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES) -> IngestionResult:
    """Validate and copy one CSV byte-for-byte into partitioned Bronze storage."""
    config = get_entity_config(entity_name)
    source_text = str(source_path)
    destination = build_destination_path(config, ingestion_date, run_id, bronze_root)
    if filesystem is None:
        source = Path(source_path)
        row_count = _validate_local_csv(source, config)
        target = Path(destination)
        if target.exists() and not overwrite:
            raise IngestionError(f"Bronze destination already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    else:
        # ``spark`` remains an accepted, ignored keyword for compatibility with
        # callers of the initial package. Fabric validation is intentionally
        # performed with notebookutils.fs and Python's csv module.
        del spark
        row_count = _validate_with_filesystem(
            filesystem,
            source_text,
            config,
            max_source_bytes,
        )
        parent = destination.rsplit("/", 1)[0]
        try:
            filesystem.mkdirs(parent)
            if filesystem.exists(destination):
                if not overwrite:
                    raise IngestionError(f"Bronze destination already exists: {destination}")
                filesystem.rm(destination, False)
            copied = filesystem.cp(source_text, destination, False)
            if copied is False:
                raise IngestionError(f"Filesystem copy returned false for {config.name}")
        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError(f"Unable to copy {config.name} source to {destination}") from exc
    return IngestionResult(config.name, source_text, destination, row_count)


def ingest_all(source_paths: dict[str, str | Path], ingestion_date: date | str, run_id: str, *, bronze_root: str = DEFAULT_BRONZE_ROOT, filesystem: Any | None = None, spark: Any | None = None, overwrite: bool = False, max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES) -> list[IngestionResult]:
    """Ingest all 12 entities in dependency-safe order."""
    missing = [name for name in ENTITY_CONFIGS if name not in source_paths]
    unknown = [name for name in source_paths if name not in ENTITY_CONFIGS]
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing entities: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown entities: {', '.join(unknown)}")
        raise IngestionError("Invalid source_paths; " + "; ".join(details))
    return [
        ingest_entity(name, source_paths[name], ingestion_date, run_id, bronze_root=bronze_root, filesystem=filesystem, spark=spark, overwrite=overwrite, max_source_bytes=max_source_bytes)
        for name in ENTITY_CONFIGS
    ]
