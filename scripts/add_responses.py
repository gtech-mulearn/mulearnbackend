#!/usr/bin/env python
"""
Second-pass script: adds responses= to @extend_schema decorators that are missing it.

Strategy per method (in priority order):
1. If method body has a serializer usage → use it (already handled by pass 1)
2. If any sibling method in the same class has a serializer → reuse it
3. If module has a serializer matching the class name → use it
4. Fallback → use CustomResponseSerializer from utils.schema_utils

Run from mulearnbackend/ root:
  python scripts/add_responses.py              # all modules
  python scripts/add_responses.py api/dashboard/mentor
"""
import ast
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
API_DIR = BASE_DIR / "api"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
FALLBACK = "CustomResponseSerializer"
FALLBACK_IMPORT = "from utils.schema_utils import CustomResponseSerializer"


def get_serializer_names_from_file(serializer_file: Path) -> list[str]:
    """Return all serializer class names defined in a file."""
    try:
        source = serializer_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and "Serializer" in node.name:
            names.append(node.name)
    return names


def find_serializer_for_class(class_name: str, serializer_names: list[str]) -> str | None:
    """Try to match a view class name to a serializer by naming convention."""
    base = re.sub(r"(API|APIView|View|CRUD)$", "", class_name).strip()
    candidates = [
        f"{base}Serializer",
        f"{base}ListSerializer",
        f"{base}DetailSerializer",
        f"{base}ResponseSerializer",
    ]
    for c in candidates:
        if c in serializer_names:
            return c
    # Partial match: serializer name contains the base
    for s in serializer_names:
        if base.lower() in s.lower() or s.lower().replace("serializer", "") in base.lower():
            return s
    return None


def find_class_serializers(view_source: str, class_name: str) -> str | None:
    """Look at all methods in the class for any serializer usage."""
    try:
        tree = ast.parse(view_source)
    except Exception:
        return None
    lines = view_source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for method in node.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            body = "\n".join(lines[method.lineno:method.end_lineno])
            for match in re.finditer(r"((?:\w+\.)?(?:\w+Serializer))\s*\(", body):
                name = match.group(1)
                if name and not name.endswith(".Serializer") and "BaseSerializer" not in name:
                    return name
    return None


def method_has_responses(decorator_text: str) -> bool:
    return "responses=" in decorator_text or "response=" in decorator_text.lower()


def get_decorator_span(lines: list[str], decorator_start: int) -> tuple[int, int]:
    """Find the end line of a decorator (handles multi-line)."""
    depth = 0
    for i in range(decorator_start, len(lines)):
        depth += lines[i].count("(") - lines[i].count(")")
        if depth <= 0 and i > decorator_start:
            return decorator_start, i
        if depth == 0 and i == decorator_start:
            return decorator_start, decorator_start
    return decorator_start, decorator_start


def patch_file(file_path: Path, serializer_names: list[str]) -> int:
    source = file_path.read_text(encoding="utf-8")
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0

    patches: list[tuple[int, int, str]] = []  # (start_line_0idx, end_line_0idx, new_text)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases_str = " ".join(ast.unparse(b) for b in node.bases)
        if "View" not in bases_str:
            continue

        # Find class-level serializer (any method in this class)
        class_serializer = find_class_serializers(source, node.name)
        # Try name-based match as fallback
        name_match = find_serializer_for_class(node.name, serializer_names)

        for method in node.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            if method.name not in HTTP_METHODS:
                continue

            # Find the @extend_schema decorator on this method
            for dec in method.decorator_list:
                dec_text = ast.unparse(dec)
                if "extend_schema" not in dec_text:
                    continue
                if method_has_responses(dec_text):
                    continue  # already has responses=

                # Determine what responses= to add
                serializer = class_serializer or name_match or FALLBACK

                # Find actual line span of this decorator
                dec_line = dec.lineno - 1  # 0-indexed
                dec_end = dec.end_lineno - 1  # 0-indexed

                # Get indentation
                def_line = lines[method.lineno - 1]
                indent = " " * (len(def_line) - len(def_line.lstrip()))

                # Rebuild decorator with responses= appended
                original = "\n".join(lines[dec_line:dec_end + 1])
                stripped = original.rstrip()
                if stripped.endswith(")"):
                    # Strip the closing ) and any whitespace/comma before it
                    core = stripped[:-1].rstrip()
                    sep = "," if not core.endswith(",") else ""
                    new_dec = core + f"{sep}\n{indent}    responses={{200: {serializer}}},\n{indent})"
                else:
                    new_dec = stripped + f", responses={{200: {serializer}}})"

                patches.append((dec_line, dec_end, new_dec))

    if not patches:
        return 0

    # Ensure fallback import is present if we used it
    used_fallback = any(FALLBACK in p[2] for p in patches)
    has_fallback_import = FALLBACK_IMPORT in source or "schema_utils" in source

    # Apply patches in reverse order
    for start, end, new_text in sorted(patches, key=lambda x: x[0], reverse=True):
        lines[start:end + 1] = new_text.splitlines()

    if used_fallback and not has_fallback_import:
        last_import_end = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and getattr(node, "col_offset", 0) == 0:
                end = getattr(node, "end_lineno", node.lineno)
                if end > last_import_end:
                    last_import_end = end
        lines.insert(last_import_end, FALLBACK_IMPORT)

    result = "\n".join(lines)
    if source.endswith("\n"):
        result += "\n"
    file_path.write_text(result, encoding="utf-8")
    return len(patches)


def collect_view_files(root: Path) -> list[Path]:
    files = list(root.rglob("*views*.py")) + list(root.rglob("*view.py"))
    return sorted({f for f in files if "__pycache__" not in str(f)})


def get_module_serializers(view_file: Path) -> list[str]:
    """Find all serializer names available in the same module directory."""
    module_dir = view_file.parent
    names = []
    for sf in module_dir.rglob("*serial*.py"):
        names.extend(get_serializer_names_from_file(sf))
    return names


def main():
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else API_DIR
    view_files = collect_view_files(target)

    total = 0
    for vf in view_files:
        serializer_names = get_module_serializers(vf)
        count = patch_file(vf, serializer_names)
        if count:
            print(f"  +{count:3d}  {vf.relative_to(BASE_DIR)}")
            total += count

    print(f"\nTotal: {total} responses= added across {len(view_files)} view files.")


if __name__ == "__main__":
    main()
