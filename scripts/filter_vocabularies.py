#!/usr/bin/env python3
"""Canonical municipality and cause vocabularies for web filter assets."""

import argparse
import collections
import csv
import gzip
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVINCE_PREFIX = {"alicante": "03", "castellon": "12", "valencia": "46"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value, pretty=False):
    options = {"ensure_ascii": False, "allow_nan": False}
    if pretty:
        options["indent"] = 2
    else:
        options.update({"sort_keys": True, "separators": (",", ":")})
    return (json.dumps(value, **options) + "\n").encode("utf-8")


def write_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def metrics(payload):
    return {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def normalize_alias(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def is_blank(value):
    return value is None or not str(value).strip()


def province_key(value):
    normalized = normalize_alias(value)
    if "alacant" in normalized or "alicante" in normalized:
        return "alicante"
    if "castell" in normalized:
        return "castellon"
    if "val" in normalized:
        return "valencia"
    return None


def bilingual_signature(value):
    parts = [normalize_alias(part) for part in re.split(r"\s*/\s*", str(value or ""))]
    parts = sorted(set(part for part in parts if part))
    return tuple(parts) if len(parts) > 1 else None


class MunicipalityResolver:
    def __init__(self, catalog, settings):
        self.entries = {}
        exact = collections.defaultdict(set)
        bilingual = collections.defaultdict(set)
        alias_fields = settings["alias_fields"]
        for feature in catalog["features"]:
            properties = feature["properties"]
            identifier = str(properties[settings["identifier_field"]])
            province = next((key for key, prefix in PROVINCE_PREFIX.items() if identifier.startswith(prefix)), None)
            aliases = []
            for field in alias_fields:
                value = properties.get(field)
                if value not in (None, ""):
                    aliases.append(str(value))
            entry = {
                "municipality_id": identifier,
                "municipality_name": properties[settings["display_field"]],
                "province_key": province,
                "official_aliases": sorted(set(aliases)),
            }
            self.entries[identifier] = entry
            for alias in aliases:
                exact[(province, normalize_alias(alias))].add(identifier)
                signature = bilingual_signature(alias)
                if signature:
                    bilingual[(province, signature)].add(identifier)
                for part in re.split(r"\s*/\s*", alias):
                    if normalize_alias(part):
                        exact[(province, normalize_alias(part))].add(identifier)
            language_names = [properties.get("nom_mun_val"), properties.get("nom_mun_cas")]
            signature = tuple(sorted(set(normalize_alias(value) for value in language_names if value)))
            if len(signature) > 1:
                bilingual[(province, signature)].add(identifier)
        self.exact = exact
        self.bilingual = bilingual
        self.documented = {}
        for alias in settings.get("documented_historical_aliases", []):
            identifier = str(alias["municipality_id"])
            if identifier not in self.entries:
                raise ValueError("Documented municipality ID is absent from official catalog: " + identifier)
            if self.entries[identifier]["province_key"] != alias["province"]:
                raise ValueError("Documented municipality alias province does not match official code: " + identifier)
            key = (alias["province"], normalize_alias(alias["municipality_raw"]))
            if key in self.documented:
                raise ValueError("Duplicate documented municipality alias: " + alias["municipality_raw"])
            self.documented[key] = {**alias, "municipality_id": identifier}
        self.review_candidates = collections.defaultdict(list)
        for candidate in settings.get("review_candidates", []):
            identifier = str(candidate["municipality_id"])
            if identifier not in self.entries:
                raise ValueError("Review candidate municipality ID is absent from official catalog: " + identifier)
            if self.entries[identifier]["province_key"] != candidate["province"]:
                raise ValueError("Review candidate province does not match official code: " + identifier)
            key = (candidate["province"], normalize_alias(candidate["municipality_raw"]))
            self.review_candidates[key].append({**candidate, "municipality_id": identifier})

    def component_candidates(self, raw, province):
        candidates = set()
        for part in re.split(r"\s*/\s*", str(raw or "")):
            candidates.update(self.exact.get((province, normalize_alias(part)), set()))
        return candidates

    def candidate_details(self, raw, province, source_identifier=None):
        candidates = collections.defaultdict(lambda: {"methods": set(), "evidence": []})
        for identifier in self.component_candidates(raw, province):
            candidates[identifier]["methods"].add("exact_official_component")
        documented = self.documented.get((province, normalize_alias(raw)))
        if documented:
            identifier = documented["municipality_id"]
            candidates[identifier]["methods"].add("documented_historical_alias")
            candidates[identifier]["evidence"].append({"url": documented["evidence_url"], "description": documented["evidence"]})
        if source_identifier and str(source_identifier) in self.entries:
            identifier = str(source_identifier)
            if not province or self.entries[identifier]["province_key"] == province:
                candidates[identifier]["methods"].add("validated_source_identifier")
        for candidate in self.review_candidates.get((province, normalize_alias(raw)), []):
            candidates[candidate["municipality_id"]]["methods"].add(candidate["basis"])
        return [
            {"municipality_id": identifier, "municipality_name": self.entries[identifier]["municipality_name"],
             "methods": sorted(value["methods"]), "evidence": value["evidence"]}
            for identifier, value in sorted(candidates.items())
        ]

    def resolve(self, raw, province=None, source_identifier=None, enhanced=True):
        if is_blank(raw):
            return {"status": "missing", "municipality_id": None, "municipality_name": None, "candidates": []}
        candidates = set(self.exact.get((province, normalize_alias(raw)), set()))
        method = "official_alias"
        if not candidates:
            signature = bilingual_signature(raw)
            if signature:
                candidates = set(self.bilingual.get((province, signature), set()))
                method = "official_bilingual_alias"
        if not candidates and province is None:
            candidates = set().union(*(values for (item_province, alias), values in self.exact.items() if alias == normalize_alias(raw)))
            method = "globally_unique_official_alias"
        if source_identifier:
            source_identifier = str(source_identifier)
            if source_identifier in candidates:
                candidates = {source_identifier}
                method = "source_identifier_and_official_alias"
            elif not candidates and source_identifier in self.entries:
                source_entry = self.entries[source_identifier]
                if not province or source_entry["province_key"] == province:
                    candidates = {source_identifier}
                    method = "validated_source_identifier"
        if enhanced and not candidates:
            documented = self.documented.get((province, normalize_alias(raw)))
            if documented:
                candidates = {documented["municipality_id"]}
                method = "documented_historical_alias"
        if enhanced and not candidates:
            component_candidates = self.component_candidates(raw, province)
            if len(component_candidates) == 1:
                candidates = component_candidates
                method = "exact_official_bilingual_component"
        if len(candidates) == 1:
            identifier = next(iter(candidates))
            return {"status": "resolved", "method": method, **self.entries[identifier], "candidates": [identifier]}
        return {
            "status": "ambiguous" if candidates else "unresolved",
            "municipality_id": None,
            "municipality_name": None,
            "candidates": sorted(candidates),
        }


def enrich_record(record, source, resolver, cause_config):
    raw_municipality = record.get("municipality_raw", record.get("municipality"))
    raw_cause = record.get("cause_raw", record.get("cause"))
    source_identifier = record.get("municipality_source_id")
    province = province_key(record.get("province"))
    initial = resolver.resolve(raw_municipality, province, source_identifier, enhanced=False)
    resolved = resolver.resolve(raw_municipality, province, source_identifier, enhanced=True)
    cause_code = cause_config["raw_mapping"].get(raw_cause) if not is_blank(raw_cause) else None
    record.pop("municipality", None)
    record.pop("cause", None)
    record.update({
        "municipality_raw": raw_municipality,
        "municipality_id": resolved["municipality_id"],
        "municipality_name": resolved["municipality_name"],
        "cause_raw": raw_cause,
        "cause_code": cause_code,
        "cause_label": cause_config["categories"].get(cause_code),
    })
    return {
        "source": source,
        "year": record.get("year"),
        "province": record.get("province"),
        "province_key": province,
        "source_municipality_id": source_identifier,
        "municipality_raw": raw_municipality,
        "initial_municipality_status": initial["status"],
        "municipality_status": resolved["status"],
        "municipality_method": resolved.get("method"),
        "municipality_id": resolved["municipality_id"],
        "municipality_name": resolved["municipality_name"],
        "municipality_candidates": resolved["candidates"],
        "candidate_details": resolver.candidate_details(raw_municipality, province, source_identifier),
        "cause_raw": raw_cause,
        "cause_code": cause_code,
    }


def unresolved_audit(audit_rows):
    groups = collections.defaultdict(list)
    for row in audit_rows:
        if row["initial_municipality_status"] in {"unresolved", "ambiguous"}:
            groups[row["municipality_raw"]].append(row)
    result = []
    for raw, rows in sorted(groups.items()):
        final_ids = {row["municipality_id"] for row in rows if row["municipality_id"]}
        final_methods = {row["municipality_method"] for row in rows if row["municipality_method"]}
        candidates = {}
        for row in rows:
            for candidate in row["candidate_details"]:
                current = candidates.setdefault(candidate["municipality_id"], {**candidate, "methods": set(), "evidence": []})
                current["methods"].update(candidate["methods"])
                for evidence in candidate["evidence"]:
                    if evidence not in current["evidence"]:
                        current["evidence"].append(evidence)
        candidates = [{**value, "methods": sorted(value["methods"])} for value in candidates.values()]
        non_municipal = "otra provincia" in normalize_alias(raw) or "iniciado otra provincia" in normalize_alias(raw)
        if len(final_ids) == 1:
            recommendation = "resolve_safe"
            if "documented_historical_alias" in final_methods:
                reason = "El catálogo actual omite la denominación histórica, pero un decreto oficial del BOE documenta el cambio de nombre del mismo municipio."
            else:
                reason = "La etiqueta bilingüe completa no es un alias exacto, pero sus componentes oficiales exactos convergen en un único municipio de la provincia indicada."
        elif non_municipal:
            recommendation = "keep_unresolved"
            reason = "El valor fuente describe un caso iniciado en otra provincia, no un municipio."
        else:
            recommendation = "needs_human_review"
            reason = "No existe código municipal fuente, alias/componente oficial exacto ni equivalencia histórica documentada que demuestre la identidad; los candidatos indicados son solo textuales o abreviados."
        result.append({
            "municipality_raw": raw,
            "record_count": len(rows),
            "sources": sorted({row["source"] for row in rows}),
            "years": sorted({row["year"] for row in rows if row["year"] is not None}),
            "provinces": sorted({row["province"] for row in rows if row["province"]}),
            "source_municipality_ids": sorted({str(row["source_municipality_id"]) for row in rows if row["source_municipality_id"]}),
            "possible_official_candidates": candidates,
            "current_reason": reason,
            "recommendation": recommendation,
            "final_status": "resolved" if len(final_ids) == 1 else "unresolved",
            "final_municipality_id": next(iter(final_ids)) if len(final_ids) == 1 else None,
            "final_municipality_name": rows[0]["municipality_name"] if len(final_ids) == 1 else None,
            "resolution_methods": sorted(final_methods),
        })
    return result


def summarize(audit_rows, resolver, cause_config):
    raw_municipalities = collections.Counter((row["source"], row["municipality_raw"]) for row in audit_rows if not is_blank(row["municipality_raw"]))
    raw_causes = collections.Counter((row["source"], row["cause_raw"]) for row in audit_rows if not is_blank(row["cause_raw"]))
    groups = collections.defaultdict(lambda: collections.Counter())
    for row in audit_rows:
        if row["municipality_id"]:
            groups[row["municipality_id"]][row["municipality_raw"]] += 1
    unresolved = collections.Counter((row["source"], row["municipality_raw"]) for row in audit_rows if row["municipality_status"] == "unresolved")
    ambiguous = collections.defaultdict(lambda: {"count": 0, "candidates": set()})
    for row in audit_rows:
        if row["municipality_status"] == "ambiguous":
            key = (row["source"], row["municipality_raw"])
            ambiguous[key]["count"] += 1
            ambiguous[key]["candidates"].update(row["municipality_candidates"])
    unclassified_causes = collections.Counter((row["source"], row["cause_raw"]) for row in audit_rows if not is_blank(row["cause_raw"]) and not row["cause_code"])
    initial_audit = unresolved_audit(audit_rows)
    return {
        "schema_version": 1,
        "municipalities": {
            "official_catalog_entries": len(resolver.entries),
            "raw_distinct_count": len({raw for source, raw in raw_municipalities}),
            "raw_distinct_by_source": {source: len({raw for item_source, raw in raw_municipalities if item_source == source}) for source in sorted({source for source, raw in raw_municipalities})},
            "canonical_used_count": len(groups),
            "resolved_record_count": sum(row["municipality_status"] == "resolved" for row in audit_rows),
            "missing_record_count": sum(row["municipality_status"] == "missing" for row in audit_rows),
            "ambiguous_record_count": sum(item["count"] for item in ambiguous.values()),
            "unresolved_record_count": sum(unresolved.values()),
            "variant_groups": [
                {"municipality_id": identifier, "municipality_name": resolver.entries[identifier]["municipality_name"], "raw_values": dict(sorted(values.items()))}
                for identifier, values in sorted(groups.items()) if len(values) > 1
            ],
            "ambiguous": [
                {"source": source, "municipality_raw": raw, "count": value["count"], "candidate_ids": sorted(value["candidates"])}
                for (source, raw), value in sorted(ambiguous.items())
            ],
            "unresolved": [
                {"source": source, "municipality_raw": raw, "count": count}
                for (source, raw), count in sorted(unresolved.items())
            ],
            "initial_unresolved_value_count": len(initial_audit),
            "initial_unresolved_record_count": sum(item["record_count"] for item in initial_audit),
            "initial_unresolved_audit": initial_audit,
        },
        "causes": {
            "raw_distinct_count": len({raw for source, raw in raw_causes}),
            "raw_distinct_by_source": {source: len({raw for item_source, raw in raw_causes if item_source == source}) for source in sorted({source for source, raw in raw_causes})},
            "canonical_categories": cause_config["categories"],
            "mapping": [
                {"source": source, "cause_raw": raw, "count": count, "cause_code": cause_config["raw_mapping"].get(raw), "cause_label": cause_config["categories"].get(cause_config["raw_mapping"].get(raw))}
                for (source, raw), count in sorted(raw_causes.items())
            ],
            "unclassified": [
                {"source": source, "cause_raw": raw, "count": count}
                for (source, raw), count in sorted(unclassified_causes.items())
            ],
            "non_equivalence_notes": cause_config["non_equivalence_notes"],
        },
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config/ui-vocabularies.json")
    parser.add_argument("--fires", type=Path, default=ROOT / "data/web/gva/fires.json")
    parser.add_argument("--recent-dir", type=Path, default=ROOT / "data/web/gva/recent")
    parser.add_argument("--dataset-manifest", type=Path, default=ROOT / "config/datasets-gva.json")
    parser.add_argument("--report", type=Path, default=ROOT / "data/derived/gva/data-ux-1/report.json")
    parser.add_argument("--audit-csv", type=Path, default=ROOT / "data/derived/gva/data-ux-1/municipality_unresolved_audit.csv")
    return parser.parse_args()


def main():
    args = parse_args()
    config = read_json(args.config)
    municipality_settings = config["municipalities"]
    catalog = read_json(ROOT / municipality_settings["catalog_path"])
    resolver = MunicipalityResolver(catalog, municipality_settings)
    cause_config = config["causes"]
    audit_rows = []

    fires_payload = read_json(args.fires)
    for record in fires_payload["fires"]:
        audit_rows.append(enrich_record(record, "icv", resolver, cause_config))
    fires_bytes = canonical_bytes(fires_payload)
    write_atomic(args.fires, fires_bytes)

    recent_manifest_path = args.recent_dir / "assets-manifest.json"
    recent_manifest = read_json(recent_manifest_path)
    for asset in recent_manifest["assets"]:
        if asset["kind"] not in {"sigif_points", "effis_perimeters"}:
            continue
        path = ROOT / asset["url"]
        payload = read_json(path)
        source = "sigif" if asset["kind"] == "sigif_points" else "effis"
        for feature in payload["features"]:
            audit_rows.append(enrich_record(feature["properties"], source, resolver, cause_config))
        data = canonical_bytes(payload)
        write_atomic(path, data)
        asset.update(metrics(data))
    transformation = "municipality and cause filter fields canonicalized from documented vocabularies; raw values retained"
    if transformation not in recent_manifest["transformations"]:
        recent_manifest["transformations"].append(transformation)
    write_atomic(recent_manifest_path, canonical_bytes(recent_manifest, pretty=True))

    dataset_manifest = read_json(args.dataset_manifest)
    fires_asset = dataset_manifest["attributes"]["fires"]
    old_metrics = {key: fires_asset[key] for key in ("bytes", "gzip_bytes")}
    fires_asset.update(metrics(fires_bytes))
    subset = dataset_manifest["production_subset"]
    subset["raw_bytes"] += fires_asset["bytes"] - old_metrics["bytes"]
    subset["gzip_bytes"] += fires_asset["gzip_bytes"] - old_metrics["gzip_bytes"]
    operation = "canonical_municipality_and_cause_filter_fields"
    if operation not in dataset_manifest["derivation"]["operations"]:
        dataset_manifest["derivation"]["operations"].append(operation)
    write_atomic(args.dataset_manifest, canonical_bytes(dataset_manifest, pretty=True))

    report = summarize(audit_rows, resolver, cause_config)
    report["inputs"] = {
        "municipality_catalog": municipality_settings["catalog_path"],
        "municipality_catalog_source_url": municipality_settings["source_url"],
        "fires": str(args.fires.relative_to(ROOT)),
        "recent_manifest": str(recent_manifest_path.relative_to(ROOT)),
    }
    write_atomic(args.report, canonical_bytes(report, pretty=True))
    args.audit_csv.parent.mkdir(parents=True, exist_ok=True)
    temporary_csv = args.audit_csv.with_name(args.audit_csv.name + ".part")
    with temporary_csv.open("w", encoding="utf-8", newline="") as stream:
        fields = ["municipality_raw", "record_count", "sources", "years", "provinces", "source_municipality_ids", "possible_official_candidates", "current_reason", "recommendation", "final_status", "final_municipality_id", "final_municipality_name", "resolution_methods"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in report["municipalities"]["initial_unresolved_audit"]:
            writer.writerow({key: json.dumps(item[key], ensure_ascii=False) if isinstance(item[key], (list, dict)) else item[key] for key in fields})
    os.replace(temporary_csv, args.audit_csv)
    print(json.dumps({
        "report": str(args.report),
        "municipality_raw": report["municipalities"]["raw_distinct_count"],
        "municipality_canonical": report["municipalities"]["canonical_used_count"],
        "municipality_ambiguous": report["municipalities"]["ambiguous_record_count"],
        "municipality_unresolved": report["municipalities"]["unresolved_record_count"],
        "cause_raw": report["causes"]["raw_distinct_count"],
        "cause_unclassified": len(report["causes"]["unclassified"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
