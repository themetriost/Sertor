"""T014 — parse_diff: file/hunk/intervalli/identificatori; binari skip; rename; added/deleted."""

from __future__ import annotations

from speclift.domain.models import RawDiff
from speclift.stages.parse_diff import parse_diff

MODIFY = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,5 @@ class Widget:
 context line
-    old_value = 1
+    def compute_total(self):
+        return 42
+    new_attr = 7
"""

ADDED = """diff --git a/new_mod.py b/new_mod.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/new_mod.py
@@ -0,0 +1,2 @@
+def hello():
+    pass
"""

DELETED = """diff --git a/gone.py b/gone.py
deleted file mode 100644
index 4444444..0000000
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def obsolete():
-    pass
"""

RENAMED = """diff --git a/old_name.py b/new_name.py
similarity index 95%
rename from old_name.py
rename to new_name.py
index 5555555..6666666 100644
--- a/old_name.py
+++ b/new_name.py
@@ -1,1 +1,1 @@
-x = 1
+x = 2
"""

BINARY = """diff --git a/logo.png b/logo.png
index 7777777..8888888 100644
Binary files a/logo.png and b/logo.png differ
"""

MULTI_HUNK = """diff --git a/multi.py b/multi.py
index 9999999..aaaaaaa 100644
--- a/multi.py
+++ b/multi.py
@@ -1,2 +1,3 @@
 a
+b
 c
@@ -20,2 +21,2 @@ def tail():
-d
+e
"""


G6_PY = """diff --git a/m.py b/m.py
index 1111111..2222222 100644
--- a/m.py
+++ b/m.py
@@ -1,1 +1,5 @@
+TOP_CONST = 1
+def real_fn():
+    local_var = 2
+    return local_var
"""

G6_RUST = """diff --git a/m.rs b/m.rs
index 1111111..2222222 100644
--- a/m.rs
+++ b/m.rs
@@ -1,1 +1,3 @@
+fn run() {
+    let temp = compute();
+}
"""


def _raw(text: str) -> RawDiff:
    return RawDiff(ref="HEAD", kind="commit", text=text)


def test_empty_diff_yields_no_files():
    cs = parse_diff(_raw("   \n"))
    assert cs.files == []
    assert cs.is_empty


def test_modify_file_and_ranges():
    cs = parse_diff(_raw(MODIFY))
    assert len(cs.files) == 1
    fc = cs.files[0]
    assert fc.path == "src/app.py"
    assert fc.change_type == "modified"
    assert not fc.is_binary
    assert len(fc.hunks) == 1
    h = fc.hunks[0]
    assert h.old_range == (10, 3)
    assert h.new_range == (10, 5)


def test_candidate_identifiers_extracted():
    cs = parse_diff(_raw(MODIFY))
    ids = cs.files[0].hunks[0].candidate_identifiers
    assert "compute_total" in ids
    # il nome della classe nel context dell'header @@ ... @@ è un buon candidato
    assert "Widget" in ids


def test_added_file():
    cs = parse_diff(_raw(ADDED))
    fc = cs.files[0]
    assert fc.path == "new_mod.py"
    assert fc.change_type == "added"
    assert "hello" in fc.hunks[0].candidate_identifiers


def test_deleted_file():
    cs = parse_diff(_raw(DELETED))
    fc = cs.files[0]
    assert fc.path == "gone.py"
    assert fc.change_type == "deleted"


def test_renamed_file():
    cs = parse_diff(_raw(RENAMED))
    fc = cs.files[0]
    assert fc.change_type == "renamed"
    assert fc.old_path == "old_name.py"
    assert fc.path == "new_name.py"


def test_binary_file_skips_content():
    cs = parse_diff(_raw(BINARY))
    fc = cs.files[0]
    assert fc.is_binary
    assert fc.hunks == []


def test_multiple_hunks():
    cs = parse_diff(_raw(MULTI_HUNK))
    fc = cs.files[0]
    assert len(fc.hunks) == 2
    assert fc.hunks[0].new_range == (1, 3)
    assert fc.hunks[1].new_range == (21, 2)


def test_g6_module_level_assign_captured_local_not():
    """G6: assegnazione top-level e `def` catturate; variabile locale indentata NO (rumore)."""
    ids = parse_diff(_raw(G6_PY)).files[0].hunks[0].candidate_identifiers
    assert "TOP_CONST" in ids
    assert "real_fn" in ids
    assert "local_var" not in ids


def test_g6_rust_let_local_not_captured():
    """G6: `fn` catturato; `let` (variabile locale) NO."""
    ids = parse_diff(_raw(G6_RUST)).files[0].hunks[0].candidate_identifiers
    assert "run" in ids
    assert "temp" not in ids
