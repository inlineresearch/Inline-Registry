#Validate the model lists the app fetches.
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
PUBLISHED = ROOT / "models.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
REQUIRED = ("id", "filename", "category", "source", "group")
KINDS = ("hf_file", "hf_folder", "url")
CATEGORIES = (
    "diffusion_models", "vae", "text_encoders", "loras", "controlnet", "checkpoints",
    "clip_vision", "upscale_models", "embeddings", "annotators", "model_patches",
    "latent_upscale_models", "characters",
)


def check_entry(entry: Any, where: str) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{where}: every entry must be a JSON object"]
    problems: list[str] = []
    ident = entry.get("id", "")
    for key in REQUIRED:
        if not entry.get(key):
            problems.append(f"{where}: {ident or '?'} is missing {key!r}")
    if ident and not ID_RE.match(ident):
        problems.append(f"{where}: id {ident!r} must be lowercase letters, digits and hyphens")
    category = entry.get("category", "")
    if category and category not in CATEGORIES:
        problems.append(f"{where}: {ident} has unknown category {category!r}")

    source = entry.get("source")
    if isinstance(source, dict):
        kind = source.get("kind")
        if kind not in KINDS:
            problems.append(f"{where}: {ident} source.kind must be one of {', '.join(KINDS)}")
        elif kind == "url":
            if not str(source.get("url", "")).startswith("https://"):
                problems.append(f"{where}: {ident} source.url must be https")
        elif not source.get("repo"):
            problems.append(f"{where}: {ident} needs source.repo")
        elif not source.get("path") and not source.get("files"):
            # A folder at the repo root names its files, so it cannot pull a sibling it must not.
            problems.append(f"{where}: {ident} needs source.path or source.files")
    elif source is not None:
        problems.append(f"{where}: {ident} source must be an object")

    size = entry.get("size_bytes")
    if size is not None and (not isinstance(size, int) or size <= 0):
        problems.append(f"{where}: {ident} size_bytes must be a positive integer or null")
    return problems


def check_file(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        return [], [f"{path.name}: missing"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [], [f"{path.name}: invalid JSON ({error})"]
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return [], [f"{path.name}: needs an 'entries' array"]

    problems: list[str] = []
    ids: set[str] = set()
    sources: set[tuple[str, str]] = set()
    for entry in entries:
        problems.extend(check_entry(entry, path.name))
        if not isinstance(entry, dict):
            continue
        ident = str(entry.get("id", ""))
        if ident in ids:
            problems.append(f"{path.name}: duplicate id {ident!r}")
        ids.add(ident)
        # One list, so everything in it is offered by default: an unverified entry belongs in a
        # separate channel, which is what models.dev.json was and will be again when one exists.
        if not entry.get("verified"):
            problems.append(f"{path.name}: {ident} is not verified")
        # A filename may appear twice (two repos carry it), but never from the same source.
        key = (str(entry.get("filename", "")), json.dumps(entry.get("source") or {}, sort_keys=True))
        if key in sources:
            problems.append(f"{path.name}: {ident} repeats a filename from the same source")
        sources.add(key)
    return [e for e in entries if isinstance(e, dict)], problems


def main() -> int:
    published, problems = check_file(PUBLISHED)
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        return 1
    print(f"models.json {len(published)} entries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
