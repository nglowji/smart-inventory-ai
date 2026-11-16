"""Keep transport, SQL and core dependencies in their agreed layers."""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def test_module_dependency_boundaries():
    violations = []
    sql_builders = {"select", "insert", "update", "delete", "func", "joinedload"}
    for path in APP_ROOT.rglob("*.py"):
        relative = path.relative_to(APP_ROOT)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            module = node.module
            if path.name == "api.py" and module.startswith("sqlalchemy"):
                if sql_builders.intersection(alias.name for alias in node.names):
                    violations.append(f"{relative}: SQL belongs in queries/service, not API")
            if path.name in {"service.py", "queries.py", "serializers.py"}:
                if module.startswith("fastapi") or module.endswith(".api"):
                    violations.append(f"{relative}: persistence/business code imports HTTP layer")
            if relative.parts[0] in {"core", "db"} and module.startswith("app.modules"):
                violations.append(f"{relative}: shared infrastructure imports a feature")
    assert not violations, "\n".join(violations)
