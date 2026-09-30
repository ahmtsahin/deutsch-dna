from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(name: str) -> dict:
    return json.loads((ROOT / ".claude-plugin" / name).read_text(encoding="utf-8"))


def skill_frontmatter() -> str:
    return (ROOT / "SKILL.md").read_text(encoding="utf-8").split("---")[1]


class PluginManifestTests(unittest.TestCase):
    def test_the_plugin_version_is_the_skill_version(self):
        # Claude Code keeps users on a plugin version until it changes.
        version = re.search(r'^\s+version: "(.+)"$', skill_frontmatter(), re.M).group(1)
        self.assertEqual(read_json("plugin.json")["version"], version)

    def test_the_root_skill_loads_under_its_own_name(self):
        # A root SKILL.md is the plugin's only skill, so no skills folder or key may replace it.
        name = re.search(r"^name: (.+)$", skill_frontmatter(), re.M).group(1)
        manifest = read_json("plugin.json")
        self.assertEqual(manifest["name"], name)
        self.assertNotIn("skills", manifest)
        self.assertFalse((ROOT / "skills").exists())

    def test_the_marketplace_lists_the_repository_as_its_plugin(self):
        entries = read_json("marketplace.json")["plugins"]
        self.assertEqual([(entry["name"], entry["source"]) for entry in entries],
                         [(read_json("plugin.json")["name"], "./")])
        self.assertNotIn("skills", entries[0])


if __name__ == "__main__":
    unittest.main()
