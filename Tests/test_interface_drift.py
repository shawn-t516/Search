import unittest

from interface_drift import compare, snapshot


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


if __name__ == "__main__":
    unittest.main()
