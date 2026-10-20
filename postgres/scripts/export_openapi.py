import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))

from quezo_api.app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Export implemented HTTP contracts without startup.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = BACKEND / "openapi.json"
    content = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            print("OpenAPI is stale. Run npm run api:generate.", file=sys.stderr)
            return 1
        print("OpenAPI is current.")
    else:
        path.write_text(content, encoding="utf-8", newline="\n")
        print("Exported postgres/openapi.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
