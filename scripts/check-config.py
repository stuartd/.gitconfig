#!/usr/bin/env python3
"""Compare reference preferences with global Git settings without changing either."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys


PLATFORMS = {"macos": "macOS", "linux": "Linux", "windows": "Windows"}
IGNORED_KEYS = set()
# Boolean (or boolean-or-text) preferences used by the reference configs.
BOOLEAN_KEYS = {
    "commit.verbose", "core.autocrlf", "diff.renames", "fetch.all",
    "fetch.prune", "pull.rebase", "push.autosetupremote", "push.followtags",
    "push.useforceifincludes", "rebase.autosquash", "rebase.autostash",
    "rebase.updaterefs", "rerere.autoupdate", "rerere.enabled",
}


@dataclass(frozen=True)
class Entry:
    origin: str
    key: str
    value: str | None


def read_config(*location: str) -> list[Entry]:
    # --get-regexp also handles a fresh machine with no global config: it
    # returns 1 and no records, whereas --list treats that as a file error.
    result = subprocess.run(
        ["git", "--no-pager", "config", *location, "--includes",
         "--show-origin", "--null", "--get-regexp", ".*"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode == 1 and not result.stdout and not result.stderr:
        return []
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip())
    fields = result.stdout.decode("utf-8", "surrogateescape").split("\0")
    if fields.pop() != "" or len(fields) % 2:
        raise RuntimeError("Unexpected output from git config.")
    entries = []
    for index in range(0, len(fields), 2):
        key, separator, value = fields[index + 1].partition("\n")
        entries.append(Entry(fields[index], key, value if separator else None))
    return entries


def origin_path(origin: str) -> Path | None:
    return Path(origin[5:]).resolve() if origin.startswith("file:") else None


def is_helper(key: str) -> bool:
    return key.startswith("credential.") and key.endswith(".helper")


def is_preference(key: str) -> bool:
    return (
        key not in IGNORED_KEYS
        and key != "include.path"
        and not (key.startswith("includeif.") and key.endswith(".path"))
    )


def group(entries: list[Entry]) -> dict[str, list[Entry]]:
    grouped = defaultdict(list)
    for entry in entries:
        if is_preference(entry.key):
            grouped[entry.key].append(entry)
    return dict(grouped)


def effective(entries: list[Entry]) -> list[Entry]:
    # Most reference preferences are scalars: the last definition wins.
    # Credential helpers accumulate in order, with an empty value resetting
    # the earlier helpers for that key. We never execute a helper or alias.
    if not is_helper(entries[0].key):
        return entries[-1:]
    helpers = []
    for entry in entries:
        if entry.value == "":
            helpers.clear()
        else:
            helpers.append(entry)
    return helpers


def comparable(entries: list[Entry]) -> list[str | None]:
    values = []
    for entry in effective(entries):
        value = entry.value
        if entry.key in BOOLEAN_KEYS:
            if value is None or value.lower() in {"true", "yes", "on"}:
                value = "true"
            elif value.lower() in {"", "false", "no", "off"}:
                value = "false"
            else:
                try:
                    value = "true" if int(value) else "false"
                except ValueError:
                    pass  # e.g. core.autocrlf=input or pull.rebase=merges
        values.append(value)
    return values


def describe(entries: list[Entry], *, all_values: bool = False) -> str:
    selected = entries if all_values and not is_helper(entries[0].key) else effective(entries)
    values = [entry.value for entry in selected]
    if not values:
        return "[] (helpers reset; none configured)"
    if len(values) == 1 and not is_helper(entries[0].key):
        return "(set without a value)" if values[0] is None else json.dumps(values[0])
    return json.dumps(values)


def print_sources(entries: list[Entry]) -> None:
    sources = dict.fromkeys(entry.origin for entry in effective(entries) or entries[-1:])
    print("    from: " + ", ".join(sources))


def check(repo: Path, platform: str) -> None:
    expected_entries = []
    for directory in ("common", platform):
        path = repo / directory / "gitconfig"
        if not path.is_file():
            raise RuntimeError(f"Reference config not found: {path}")
        expected_entries.extend(read_config("--file", str(path)))

    reference_paths = {
        (repo / directory / "gitconfig").resolve()
        for directory in ("common", *PLATFORMS)
    }
    # Include any files pulled in by the selected reference configs too.
    reference_paths.update(
        path for entry in expected_entries
        if (path := origin_path(entry.origin)) is not None
    )
    local_entries = []
    excluded_sources = set()
    for entry in read_config("--global"):
        if origin_path(entry.origin) in reference_paths:
            excluded_sources.add(entry.origin)
        else:
            local_entries.append(entry)

    expected = group(expected_entries)
    local = group(local_entries)
    missing = sorted(expected.keys() - local.keys())
    local_only = sorted(local.keys() - expected.keys())
    different = sorted(
        key for key in expected.keys() & local.keys()
        if comparable(expected[key]) != comparable(local[key])
    )
    matching = len(expected) - len(missing) - len(different)

    print(f"Git config comparison: {PLATFORMS[platform]}")
    print(f"Reference: common/gitconfig + {platform}/gitconfig")
    print("Local: global config and its includes (excluding reference files)")
    if excluded_sources:
        print("\nReference files still loaded by your global config:")
        for source in sorted(excluded_sources):
            print(f"  {source}")
        print("  Their values are excluded so they do not count as local copies.")

    print(f"\nMissing locally ({len(missing)}):")
    for key in missing:
        label = f"git alias {key[6:]}" if key.startswith("alias.") else key
        print(f"  {label} not found")
        print(f"    repo: {describe(expected[key])}")
    if not missing:
        print("  None.")

    print(f"\nDifferent values ({len(different)}):")
    for key in different:
        print(f"  {key}")
        print(f"    repo:  {describe(expected[key])}")
        print(f"    local: {describe(local[key])}")
        print_sources(local[key])
    if not different:
        print("  None.")

    print(f"\nOnly local; absent from this platform's references ({len(local_only)}):")
    for key in local_only:
        print(f"  {key}")
        print(f"    local: {describe(local[key], all_values=True)}")
        print_sources(local[key])
    if not local_only:
        print("  None.")

    print(f"\n{matching} reference settings match.")
    if IGNORED_KEYS:
        print("Ignored: " + ", ".join(sorted(IGNORED_KEYS)) + ".")
    print("Report only; no files changed. Local-only settings can be intentional.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", choices=PLATFORMS,
        help="reference platform (default: detect this machine)",
    )
    args = parser.parse_args()
    platform = args.platform
    if platform is None:
        if sys.platform == "darwin":
            platform = "macos"
        elif sys.platform.startswith("linux"):
            platform = "linux"
        elif sys.platform in {"win32", "cygwin", "msys"}:
            platform = "windows"
        else:
            parser.error("Cannot detect this platform; choose --platform explicitly.")
    try:
        check(Path(__file__).resolve().parent.parent, platform)
    except (OSError, RuntimeError) as error:
        print(f"Cannot compare Git configuration: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
