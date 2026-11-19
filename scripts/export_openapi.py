"""Write the API spec to openapi.json at the repo root. Run it after changing the API: python scripts/export_openapi.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shopflow.main import app  # noqa: E402

(ROOT / "openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print("wrote openapi.json")
