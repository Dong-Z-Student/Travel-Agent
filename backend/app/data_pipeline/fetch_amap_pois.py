from __future__ import annotations

from dataclasses import asdict

from app.data_pipeline.amap_client import AmapClient
from app.data_pipeline.clean_pois import CATEGORY_CONFIGS, clean_amap_poi, dedupe_clean_pois
from app.data_pipeline.import_pois import (
    ImportReport,
    create_import_job,
    create_pipeline_engine,
    create_session,
    finish_import_job,
    import_clean_pois,
    insert_raw_pois,
)


def fetch_and_import_pois(
    categories: list[str] | None = None,
    city: str = "武汉市",
    max_pages: int = 20,
    offset: int = 25,
    delay_seconds: float = 0.25,
    retries: int = 3,
    retry_interval: float = 1.0,
    timeout: float = 15.0,
    dry_run: bool = False,
) -> ImportReport:
    selected_categories = categories or list(CATEGORY_CONFIGS.keys())
    unknown = [category for category in selected_categories if category not in CATEGORY_CONFIGS]
    if unknown:
        raise ValueError(f"Unknown category code: {', '.join(unknown)}")

    client = AmapClient(delay_seconds=delay_seconds, retries=retries, retry_interval=retry_interval, timeout=timeout)
    report = ImportReport()

    db = None
    if not dry_run:
        engine = create_pipeline_engine()
        db = create_session(engine)
        report.job_id = create_import_job(db, "amap_poi_fetch", city)

    try:
        all_clean_pois = []
        for category_code in selected_categories:
            category = CATEGORY_CONFIGS[category_code]
            for keyword in category.keywords:
                raw_pois = []
                for page in range(1, max_pages + 1):
                    result = client.search_page(category, keyword, city, page, offset)
                    report.total_raw_count += len(result.pois)
                    raw_pois.extend(result.pois)
                    if len(result.pois) < offset:
                        break

                if db and report.job_id:
                    report.raw_inserted_count += insert_raw_pois(db, report.job_id, category_code, city, keyword, raw_pois)

                for raw in raw_pois:
                    clean = clean_amap_poi(raw, category_code, city)
                    if clean:
                        all_clean_pois.append(clean)
                    else:
                        report.failed_count += 1
                        report.errors.append(f"Skip invalid POI: category={category_code}, raw_id={raw.get('id')}")

        clean_pois = dedupe_clean_pois(all_clean_pois)
        report.clean_count = len(clean_pois)

        if db and not dry_run:
            report.poi_inserted_count, report.poi_updated_count = import_clean_pois(db, clean_pois)
            if report.job_id:
                finish_import_job(db, report.job_id, report, "success")

        return report
    except Exception as exc:
        if db:
            db.rollback()
        report.failed_count += 1
        report.errors.append(str(exc))
        if db and report.job_id:
            finish_import_job(db, report.job_id, report, "failed")
        raise
    finally:
        if db:
            db.close()


def report_to_dict(report: ImportReport) -> dict:
    return asdict(report)
