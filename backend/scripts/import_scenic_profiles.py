from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data_pipeline.import_scenic_profiles import (
    DEFAULT_BUCKET,
    DEFAULT_CSV_PATH,
    import_scenic_profiles_from_csv,
    report_to_dict,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import scenic spot profiles and images from CSV.")
    parser.add_argument("--csv-path", default=str(DEFAULT_CSV_PATH), help="CSV path relative to backend/ or absolute path.")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="Supabase Storage bucket for local image uploads.")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV, POI matching and image paths without writing data.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = import_scenic_profiles_from_csv(
        csv_path=args.csv_path,
        bucket=args.bucket,
        dry_run=args.dry_run,
    )
    print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
