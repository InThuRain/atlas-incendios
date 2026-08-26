#!/usr/bin/env python3
"""Adapt the legacy GVA source catalog to ES-2 source IDs without mutation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


class CompatibilityError(ValueError):
    pass


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def adapt_profiles(legacy: dict, national: dict, compatibility: dict) -> dict[str, list[str]]:
    mapping = compatibility["source_id_map"]
    output = {}
    profile_map = {"development": "pilot_development", "public": "pilot_public"}
    for legacy_profile, national_profile in profile_map.items():
        legacy_sources = legacy["profiles"][legacy_profile]["sources"]
        try:
            adapted = [mapping[source_id] for source_id in legacy_sources]
        except KeyError as exc:
            raise CompatibilityError(f"No national source mapping for legacy source {exc.args[0]}") from exc
        expected = national["profiles"][national_profile]
        if adapted != expected:
            raise CompatibilityError(
                f"Profile {legacy_profile} adapts to {adapted}, expected {expected}"
            )
        output[national_profile] = adapted
    return output


def validate_id_policies(compatibility: dict) -> None:
    policies = compatibility.get("published_id_policies", [])
    if not policies or any(item.get("action") != "preserve_as_primary" for item in policies):
        raise CompatibilityError("Every published ID policy must preserve the existing ID as primary")
    permalink = compatibility.get("permalink", {})
    if permalink.get("current_version") != 1 or permalink.get("action") != "resolve_legacy_ids_without_rewriting_hash":
        raise CompatibilityError("Permalink v1 compatibility contract is missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, default=Path("config/sources-gva.json"))
    parser.add_argument("--national", type=Path, default=Path("config/sources-spain.json"))
    parser.add_argument("--compatibility", type=Path, default=Path("config/compatibility-gva-v1.json"))
    args = parser.parse_args()
    legacy, national, compatibility = load(args.legacy), load(args.national), load(args.compatibility)
    profiles = adapt_profiles(legacy, national, compatibility)
    validate_id_policies(compatibility)
    print(json.dumps({
        "valid": True,
        "profiles": profiles,
        "reconciliation": compatibility["pilot_reconciliation"],
        "mutates_legacy_catalog": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompatibilityError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)
