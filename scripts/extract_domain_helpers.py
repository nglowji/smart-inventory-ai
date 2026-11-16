from pathlib import Path
import re
import os

root = Path(__file__).resolve().parents[1] / "frontend/src"
path = root / "shared/lib/format.ts"
text = path.read_text(encoding="utf-8")
text = text[:text.index("export const movementNames")]
path.write_text(text, encoding="utf-8")
for path in root.rglob("*.tsx"):
    text = path.read_text(encoding="utf-8")
    additions = []
    def rewrite(match):
        names = [name.strip() for name in match[1].split(",") if name.strip()]
        for name, target in (("movementNames", "features/inventory/model.ts"), ("belowMinimum", "features/catalog/model.ts")):
            if name in names:
                names.remove(name)
                relative = os.path.relpath(root / target, path.parent).replace("\\", "/").removesuffix(".ts")
                if not relative.startswith("."): relative = "./" + relative
                additions.append(f'import {{ {name} }} from "{relative}";\n')
        return f'import {{ {", ".join(names)} }} from "{match[2]}";' if names else ""
    text = re.sub(r'import\s*\{([^}]+)\}\s*from\s*"([^"]*lib/format)";', rewrite, text)
    text = "".join(additions) + text
    path.write_text(text, encoding="utf-8")
