#!/usr/bin/env python3
"""Replay static Settings copy against a fork's Traditional Chinese catalog on macOS."""
import argparse
import json
import subprocess
import sys

INDEX = "Sources/Search/SettingsIndex.swift"
CATALOG = "Sources/Search/Resources/zh-Hant.lproj/Interface.strings"


def output(*command, data=None):
    return subprocess.check_output(command, input=data)


def snapshot(source):
    ast = json.loads(output("xcrun", "swiftc", "-frontend", "-dump-parse",
                            "-dump-ast-format", "json", "-", data=source))
    index, = (item for item in ast["items"] if item["_kind"] == "enum_decl"
              and item["name"]["base_name"]["name"] == "SettingsIndex")
    result = {}
    tables = set()
    for member in index["members"]:
        for entry in member.get("pattern_entries", []):
            pattern = entry["pattern"].get("sub_pattern", {})
            table = pattern.get("name", {}).get("base_name", {}).get("name")
            if table not in ("groups", "items"):
                continue
            tables.add(table)
            array = entry["original_init"]
            if table == "items" and array["_kind"] == "call_expr":
                # The source filters the literal array by OS availability after construction.
                if array["fn"].get("field") != "filter":
                    raise ValueError("unrecognized SettingsIndex.items initializer")
                expr = array["fn"]["base"]["sub_expr"]
                terms = expr["elements"]
                if any(term["_kind"] != "coerce_expr" for term in terms[1:]):
                    raise ValueError("unsupported computed SettingsIndex.items")
                array = terms[0]
            if array["_kind"] != "array_expr" or not array["elements"]:
                raise ValueError(f"expected a nonempty literal array for {table}")
            for row in array["elements"]:
                if row["fn"].get("name") != "init":
                    raise ValueError(f"unsupported initializer in {table}")
                args = {arg["label"]: arg["expr"] for arg in row["args"]["args"]}
                fields = ["id", "title"] if table == "groups" else ["id", "title", "detail"]
                if "more" in args:
                    fields.append("more")
                if any(args[key]["_kind"] != "string_literal_expr" for key in fields):
                    raise ValueError(f"computed field in {table} requires review")
                for field in fields[1:]:
                    key = f"{table}/{args['id']['value']}/{field}"
                    if key in result:
                        raise ValueError(f"duplicate {key}")
                    result[key] = args[field]["value"]
    if tables != {"groups", "items"}:
        raise ValueError("SettingsIndex.groups or .items not found")
    return {key: value for key, value in result.items() if value}


def compare(before, after, translations):
    changes = []
    missing = {}
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old != new:
            kind = "changed"
            if old is None:
                kind = "added"
            elif new is None:
                kind = "removed"
            changes.append(dict(location=key, kind=kind, before=old, after=new))
        if new and not translations.get(new, "").strip():
            missing[key] = new
    return changes, missing


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("base", "head", "catalog"):
        cli.add_argument(arg, help="local Git revision")
    args = cli.parse_args()
    refs = {name: output("git", "rev-parse", "--verify", "--end-of-options",
                         rev + "^{commit}").decode().strip() for name, rev in vars(args).items()}
    before, after = (snapshot(output("git", "show", refs[name] + ":" + INDEX))
                     for name in ("base", "head"))
    catalog = output("git", "show", refs["catalog"] + ":" + CATALOG)
    translations = json.loads(output("plutil", "-convert", "json", "-o", "-", "--", "-", data=catalog))
    changes, missing = compare(before, after, translations)
    print(json.dumps(dict(revisions=refs, coverage="SettingsIndex static nonempty group and item copy",
                          base_fields=len(before), head_fields=len(after), catalog_keys=len(translations),
                          changes=changes, missing=missing), indent=2, ensure_ascii=False))
    return 1 if missing else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyError, TypeError, ValueError, IndexError, OSError, subprocess.CalledProcessError) as error:
        print(f"Cannot verify Settings copy: {error}", file=sys.stderr)
        sys.exit(2)
