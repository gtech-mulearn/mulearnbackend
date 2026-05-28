#!/usr/bin/env python
"""
Automatically adds @extend_schema decorators to all APIView HTTP methods.

Run from mulearnbackend/ root:
  python scripts/annotate_schemas.py              # all modules
  python scripts/annotate_schemas.py api/leaderboard  # single module
"""
import ast
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
API_DIR = BASE_DIR / "api"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

METHOD_ACTION_MAP = {
    "get": "Retrieve",
    "post": "Create",
    "put": "Update",
    "patch": "Partially update",
    "delete": "Delete",
}


def get_tag(file_path: Path) -> list:
    """api/dashboard/campus/campus_views.py -> ['Dashboard - Campus']"""
    parts = file_path.parts
    try:
        api_idx = list(parts).index("api")
    except ValueError:
        return ["General"]
    module_parts = list(parts[api_idx + 1 : -1])
    if not module_parts:
        return ["General"]
    return [" - ".join(p.replace("_", " ").title() for p in module_parts)]


def camel_to_words(name: str) -> str:
    """CampusDetailsAPI -> 'Campus Details'"""
    name = re.sub(r"(API|APIView|View|CRUD)$", "", name).strip()
    name = re.sub(r"([A-Z])", r" \1", name).strip()
    return name


def make_description(class_name: str, method: str) -> str:
    action = METHOD_ACTION_MAP.get(method, method.capitalize())
    resource = camel_to_words(class_name)
    return f"{action} {resource}."


def find_response_serializer(lines: list, start: int, end: int) -> str | None:
    """Find serializer referenced in method body (response pattern, not data=)."""
    body = "\n".join(lines[start:end])
    for match in re.finditer(r"((?:\w+\.)?(?:\w+Serializer))\s*\(", body):
        name = match.group(1)
        if not name or name.endswith(".Serializer") or "BaseSerializer" in name:
            continue
        after = body[match.end():][:20]
        if "data=" in after:
            continue
        return name
    return None


def find_request_serializer(lines: list, start: int, end: int) -> str | None:
    """Find serializer instantiated with data=request.data (request body)."""
    body = "\n".join(lines[start:end])
    matches = re.findall(r"((?:\w+\.)?(?:\w+Serializer))\s*\(\s*data\s*=", body)
    return matches[0] if matches else None


def already_annotated(method_node: ast.FunctionDef) -> bool:
    for d in method_node.decorator_list:
        if "extend_schema" in ast.unparse(d):
            return True
    return False


def annotate_file(file_path: Path) -> int:
    """Inject @extend_schema on all unannotated HTTP methods. Returns count added."""
    source = file_path.read_text(encoding="utf-8")
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  SKIP (SyntaxError): {file_path}: {e}")
        return 0

    tag = get_tag(file_path)
    tag_str = str(tag)

    insertions: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases_str = " ".join(ast.unparse(b) for b in node.bases)
        if "View" not in bases_str:
            continue

        for method in node.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            if method.name not in HTTP_METHODS:
                continue
            if already_annotated(method):
                continue

            description = make_description(node.name, method.name)
            m_start = method.lineno       # 1-indexed
            m_end = method.end_lineno     # 1-indexed

            response_s = find_response_serializer(lines, m_start, m_end)
            request_s = (
                find_request_serializer(lines, m_start, m_end)
                if method.name in {"post", "put", "patch"}
                else None
            )

            def_line = lines[m_start - 1]
            indent = " " * (len(def_line) - len(def_line.lstrip()))

            parts = [f"tags={tag_str}", f'description="{description}"']
            if request_s:
                parts.append(f"request={request_s}")
            if response_s:
                parts.append(f"responses={{200: {response_s}}}")

            if len(parts) <= 2:
                decorator = f"{indent}@extend_schema({', '.join(parts)})"
            else:
                inner = f",\n{indent}    ".join(parts)
                decorator = f"{indent}@extend_schema(\n{indent}    {inner},\n{indent})"

            insertions.append((m_start - 1, decorator))

    if not insertions:
        return 0

    if "extend_schema" not in source:
        last_import_line = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and getattr(node, "col_offset", 0) == 0:
                end = getattr(node, "end_lineno", node.lineno)
                if end > last_import_line:
                    last_import_line = end
        lines.insert(last_import_line, "from drf_spectacular.utils import extend_schema")
        insertions = [(ln + 1, dec) for ln, dec in insertions]

    for line_no, decorator in sorted(insertions, key=lambda x: x[0], reverse=True):
        lines.insert(line_no, decorator)

    result = "\n".join(lines)
    if source.endswith("\n"):
        result += "\n"
    file_path.write_text(result, encoding="utf-8")
    return len(insertions)


def collect_view_files(root: Path) -> list[Path]:
    files = list(root.rglob("*views*.py")) + list(root.rglob("*view.py"))
    return sorted({f for f in files if "__pycache__" not in str(f)})


def main():
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else API_DIR
    view_files = collect_view_files(target)

    total_annotations = 0
    for vf in view_files:
        count = annotate_file(vf)
        if count:
            print(f"  +{count:3d}  {vf.relative_to(BASE_DIR)}")
            total_annotations += count

    print(f"\nTotal: {total_annotations} decorators added across {len(view_files)} view files.")


if __name__ == "__main__":
    main()
