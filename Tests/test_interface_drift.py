import unittest

from interface_drift import compare, render_summary, snapshot


class InterfaceDriftTests(unittest.TestCase):
    def test_copy_changes_and_missing_values(self):
        before = {"a": "Old", "b": "Gone"}
        after = {"a": "New", "c": "Added"}
        changes, missing = compare(before, after, {"New": "新", "Added": " "})
        self.assertEqual([c["kind"] for c in changes], ["changed", "removed", "added"])
        self.assertEqual(missing, {"c": "Added"})
        self.assertEqual(compare(after, after, {"New": "新", "Added": "加"}), ([], {}))

    def test_source_fields_only(self):
        source = b'''enum SettingsIndex {
            static let groups: [Group] = [.init(id: "a", title: "Group")]
            static let items: [Item] = [.init(id: "a", title: "Row", detail: "", words: ["alias"])]
        }'''
        self.assertEqual(snapshot(source), {"groups/a/title": "Group", "items/a/title": "Row"})
        with self.assertRaises(ValueError):
            snapshot(source.replace(b'title: "Row"', b'title: dynamic()'))
        with self.assertRaises(ValueError):
            snapshot(source.replace(b"let items", b"let renamed"))

    def test_render_summary_missing_and_escaping(self):
        report = {
            "revisions": {"base": "111", "head": "222", "catalog": "333"},
            "coverage": "SettingsIndex static nonempty group and item copy",
            "base_fields": 2,
            "head_fields": 3,
            "catalog_keys": 1,
            "changes": [
                {"location": "items/x/title", "kind": "changed", "before": "A | [B](url)", "after": "C <D>\nE"},
                {"location": "items/y/title", "kind": "added", "before": None, "after": "C <D>\nE"},
            ],
            "missing": {"items/y/title": "C <D>\nE", "items/x/title": "C <D>\nE"},
        }
        md = render_summary(report)
        self.assertEqual(md, render_summary(report))
        self.assertIn("Missing translations: 2 locations (1 unique English strings)", md)
        self.assertIn("| items/x/title | C &lt;D&gt;<br>E |", md)
        self.assertIn("| changed | items/x/title | A &#124; &#91;B&#93;(url) | C &lt;D&gt;<br>E |", md)
        self.assertIn("| added | items/y/title | — | C &lt;D&gt;<br>E |", md)

    def test_render_summary_clean(self):
        report = {
            "revisions": {"base": "111", "head": "111", "catalog": "333"},
            "coverage": "SettingsIndex static nonempty group and item copy",
            "base_fields": 2,
            "head_fields": 2,
            "catalog_keys": 2,
            "changes": [],
            "missing": {},
        }
        md = render_summary(report)
        self.assertIn("All checked Settings fields have catalog entries (0 missing)", md)
        self.assertEqual(md.count("\nNone.\n"), 2)


if __name__ == "__main__":
    unittest.main()
