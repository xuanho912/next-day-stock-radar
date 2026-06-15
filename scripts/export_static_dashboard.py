from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "frontend" / "app"
PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"


def main() -> int:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    for path in APP_DIR.iterdir():
        if path.is_file():
            shutil.copy2(path, DIST_DIR / path.name)
    for path in PUBLIC_DIR.glob("*.json"):
        shutil.copy2(path, DIST_DIR / path.name)
    (DIST_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Static dashboard exported to {DIST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
