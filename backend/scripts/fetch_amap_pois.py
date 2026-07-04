from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data_pipeline.clean_pois import CATEGORY_CONFIGS
from app.data_pipeline.fetch_amap_pois import fetch_and_import_pois, report_to_dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Wuhan POIs from Amap and import them into Supabase/PostGIS.")
    parser.add_argument("--city", default="武汉市", help="City name passed to Amap. Default: 武汉市")
    parser.add_argument(
        "--categories",
        default=",".join(CATEGORY_CONFIGS.keys()),
        help="Comma-separated category codes. Supported: scenic_spot, hotel, metro_station",
    )
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum Amap pages per category keyword.")
    parser.add_argument("--offset", type=int, default=25, help="Page size. Amap supports up to 25 for this endpoint.")
    parser.add_argument("--delay-seconds", type=float, default=0.25, help="Delay between Amap requests.")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for each Amap request.")
    parser.add_argument("--retry-interval", type=float, default=1.0, help="Base retry interval in seconds.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and clean data without writing database records.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    categories = [item.strip() for item in args.categories.split(",") if item.strip()]
    report = fetch_and_import_pois(
        categories=categories,
        city=args.city,
        max_pages=args.max_pages,
        offset=args.offset,
        delay_seconds=args.delay_seconds,
        retries=args.retries,
        retry_interval=args.retry_interval,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
