#!/usr/bin/env python3
"""Convert Markdown+YAML subagents (<name>.md) into Codex custom agents (<name>.toml).

Usage: build_codex.py [PATH ...] [--out DIR] [--check]

PATH is a .md file or a directory of them (default: agents/ in this repository).
Output goes to --out (default: codex/ in this repository) as <name>.toml with
name (kebab-case turned into snake_case), description, and developer_instructions (the body).
--check writes nothing and exits 1 when any output is missing or differs.
"""

import argparse
import json
import re
import sys
from pathlib import Path

if sys.version_info < (3, 12):
    sys.exit("Python 3.12 or newer is required (for example: uv python install 3.12).")

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SourceError(ValueError):
    pass


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse(text: str) -> tuple[dict[str, str], str]:
    """Split frontmatter (flat `key: value`, folded continuation lines, `>`/`|` blocks) from the body."""
    if not text.startswith("---\n"):
        raise SourceError("missing frontmatter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise SourceError("unterminated frontmatter")
    fields: dict[str, str] = {}
    blocks: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        if line[:1] in (" ", "\t") and key:
            fields[key] += ("\n" if blocks.get(key) == "|" else " ") + line.strip()
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise SourceError(f"unsupported frontmatter line: {line!r}")
        key, value = key.strip(), value.strip()
        if value in (">", ">-", "|", "|-"):
            blocks[key] = value[0]
            fields[key] = ""
        else:
            fields[key] = unquote(value)
    fields = {k: v.strip() for k, v in fields.items()}
    return fields, text[end + 5 :].strip("\n") + "\n"


def toml_text(value: str) -> str:
    if "'''" in value or re.search(r"[\x00-\x08\x0b-\x1f\x7f]", value):
        return json.dumps(value, ensure_ascii=False)
    return "'''\n" + value + "'''"


def render(source: Path) -> str:
    fields, body = parse(source.read_text(encoding="utf-8"))
    name, description = fields.get("name", ""), fields.get("description", "")
    if name != source.stem or not NAME.match(name):
        raise SourceError(f"name must be kebab-case and equal the file name, got {name!r}")
    if not description:
        raise SourceError("description is required")
    if not body.strip():
        raise SourceError("body (developer instructions) is empty")
    return (
        f"# Generated from {source.name} by scripts/build_codex.py. Edit the .md source, not this file.\n"
        f"name = {json.dumps(name.replace('-', '_'))}\n"
        f"description = {json.dumps(description, ensure_ascii=False)}\n"
        f"developer_instructions = {toml_text(body)}\n"
    )


def sources(paths: list[Path]) -> list[Path]:
    found = []
    for path in paths:
        found.extend(sorted(path.glob("*.md")) if path.is_dir() else [path])
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "codex")
    parser.add_argument("--check", action="store_true", help="report differences without writing")
    args = parser.parse_args(argv)
    if not args.paths:
        if not (ROOT / "agents").is_dir():
            print("no standalone subagents: agents/ does not exist")
            return 0
        args.paths = [ROOT / "agents"]

    stale = []
    for source in sources(args.paths):
        try:
            text = render(source)
        except (OSError, SourceError) as error:
            print(f"error: {source}: {error}", file=sys.stderr)
            return 2
        target = args.out / f"{source.stem}.toml"
        if target.is_file() and target.read_text(encoding="utf-8") == text:
            continue
        stale.append(target)
        if not args.check:
            args.out.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    for target in stale:
        print(f"{'differs' if args.check else 'wrote'}: {target}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
