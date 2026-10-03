"""Verify the generated package against the original monolith.

Checks that every top-level name and every TransportApp method survived the
split, and that importing the package exposes the same public surface.
"""
import ast
import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ORIG = os.path.join("_refactor_backup", "transport_desktop_app.py")
_HAVE_ORIG = os.path.isfile(ORIG)
if not _HAVE_ORIG:
    print("### (original monolith reference removed - skipping method comparison)")
    orig_names, orig_app, orig_methods = set(), None, []
else:
    orig_tree = ast.parse(open(ORIG, encoding="utf-8-sig").read())

    def _name_of(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return node.name
        if isinstance(node, ast.Assign):
            return ast.unparse(node.targets[0])
        if isinstance(node, ast.AnnAssign):
            return ast.unparse(node.target)
        return None

    orig_names = {_name_of(n) for n in orig_tree.body}
    orig_names.discard(None)
    orig_app = next(n for n in orig_tree.body
                    if isinstance(n, ast.ClassDef) and n.name == "TransportApp")
    orig_methods = [m.name for m in orig_app.body
                    if isinstance(m, ast.FunctionDef)]

# ---- collect what the new package defines
import glob

new_names, new_methods = set(), {}
for path in glob.glob("transport/*.py"):
    mod = path.replace("\\", "/").rsplit("/", 1)[-1][:-3]
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        nm = _name_of(node) if _HAVE_ORIG else (
            node.name if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            else (ast.unparse(node.targets[0]) if isinstance(node, ast.Assign)
                  else None))
        if nm:
            new_names.add(nm)
        if isinstance(node, ast.ClassDef) and nm.endswith("Mixin"):
            for m in node.body:
                if isinstance(m, ast.FunctionDef):
                    new_methods.setdefault(m.name, []).append(mod)

# TransportApp itself is assembled from the mixins in transport/app.py
app_tree = ast.parse(open("transport/app.py", encoding="utf-8").read())
for node in app_tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "TransportApp":
        for b in node.bases:
            new_names.add(ast.unparse(b))

missing = sorted(orig_names - new_names - {"TransportApp"})
print("### top-level names missing from the package:", missing or "(none)")

missing_m = sorted(set(orig_methods) - set(new_methods))
print("### TransportApp methods missing:", missing_m or "(none)")
print(f"### methods carried over: {len(new_methods)} / {len(orig_methods)}")

dupes = {k: v for k, v in new_methods.items() if len(v) > 1}
print("### methods duplicated across mixins:", dupes or "(none)")

print("\n### per-mixin method counts")
for mod in sorted(set(m for v in new_methods.values() for m in v)):
    print(f"   {mod}: {len([k for k, v in new_methods.items() if mod in v])}")

# ---- decorator fidelity: a dropped @staticmethod is a silent runtime bug
orig_decos = {}
if _HAVE_ORIG:
    for m in orig_app.body:
        if isinstance(m, ast.FunctionDef) and m.decorator_list:
            orig_decos[m.name] = [ast.unparse(d) for d in m.decorator_list]

new_decos = {}
for path in glob.glob("transport/*.py"):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and m.decorator_list:
                    new_decos[m.name] = [ast.unparse(d) for d in m.decorator_list]

lost = {k: v for k, v in orig_decos.items() if new_decos.get(k) != v}
print(f"\n### decorators in original: {len(orig_decos)}")
print("### decorators lost/changed:", lost or "(none)")

# ---- import smoke test
print("\n### import smoke test")
try:
    import transport
    print("   import transport -> OK")
    for attr in ("TransportApp", "run_application"):
        print(f"   transport.{attr}: {'OK' if hasattr(transport, attr) else 'MISSING'}")
except Exception as exc:
    print(f"   FAILED: {type(exc).__name__}: {exc}")