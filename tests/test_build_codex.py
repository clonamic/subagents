import contextlib
import io
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_codex  # noqa: E402

SOURCE = """---
name: code-reviewer
description: >
  Reviews a diff
  and reports defects.
model: inherit
---

You review code. Quote 'single' and \"double\" marks and C:\\paths as-is.

1. Read the diff.
"""


def run(*args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return build_codex.main([str(a) for a in args])


class BuildCodexTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.src = self.dir / "agents"
        self.out = self.dir / "codex"
        self.src.mkdir()
        (self.src / "code-reviewer.md").write_text(SOURCE, encoding="utf-8")

    def test_converts_to_codex_toml(self):
        self.assertEqual(run(self.src, "--out", self.out), 0)
        data = tomllib.loads((self.out / "code-reviewer.toml").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"name", "description", "developer_instructions"})
        self.assertEqual(data["name"], "code_reviewer")
        self.assertEqual(data["description"], "Reviews a diff and reports defects.")
        self.assertEqual(data["developer_instructions"], SOURCE.split("---\n", 2)[2].lstrip("\n"))

    def test_check_detects_drift(self):
        self.assertEqual(run(self.src, "--out", self.out, "--check"), 1)
        run(self.src, "--out", self.out)
        self.assertEqual(run(self.src, "--out", self.out, "--check"), 0)
        (self.out / "code-reviewer.toml").write_text("stale", encoding="utf-8")
        self.assertEqual(run(self.src, "--out", self.out, "--check"), 1)

    def test_rejects_invalid_source(self):
        (self.src / "code-reviewer.md").write_text("---\nname: other\ndescription: x\n---\nbody\n", encoding="utf-8")
        self.assertEqual(run(self.src, "--out", self.out), 2)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
