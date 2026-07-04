from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.data_pipeline.clean_pois import CleanPoi


@dataclass
class ImportReport:
    job_id: str | None = None
    total_raw_count: int = 0
    raw_inserted_count: int = 0
    clean_count: int = 0
    poi_inserted_count: int = 0
    poi_updated_count: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)


def create_pipeline_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    parsed_url = make_url(url)
    if parsed_url.host and "@" in parsed_url.host:
        raise RuntimeError("DATABASE_URL host contains '@'. Encode special characters in the database password, for example '@' as '%40'.")
    return create_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})


def create_session(engine: Engine) -> Session:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def create_import_job(db: Session, job_type: str, city: str, source: str = "amap") -> str:
    job_id = db.execute(
        text(
            """
            insert into public.import_jobs (job_type, source, city, status, started_at)
            values (:job_type, :source, :city, 'running', now())
            returning id::text
            """
        ),
        {"job_type": job_type, "source": source, "city": city},
    ).scalar_one()
    db.commit()
    return job_id


def finish_import_job(db: Session, job_id: str, report: ImportReport, status: str = "success") -> None:
    db.execute(
        text(
            """
            update public.import_jobs
            set status = :status,
                finished_at = now(),
                total_count = :total_count,
                success_count = :success_count,
                failed_count = :failed_count,
                error_log = :error_log
            where id = :job_id
            """
        ),
        {
            "job_id": job_id,
            "status": status,
            "total_count": report.total_raw_count,
            "success_count": report.poi_inserted_count + report.poi_updated_count,
            "failed_count": report.failed_count,
            "error_log": "\n".join(report.errors) if report.errors else None,
        },
    )
    db.commit()


def insert_raw_pois(db: Session, job_id: str, category_code: str, city: str, keyword: str, raw_pois: list[dict[str, Any]]) -> int:
    if not raw_pois:
        return 0

    rows = [
        {
            "import_job_id": job_id,
            "amap_poi_id": raw.get("id"),
            "keyword": keyword,
            "category_code": category_code,
            "city": city,
            "raw_json": json.dumps(raw, ensure_ascii=False),
        }
        for raw in raw_pois
    ]
    db.execute(
        text(
            """
            insert into public.raw_amap_pois (import_job_id, amap_poi_id, keyword, category_code, city, raw_json)
            values (:import_job_id, :amap_poi_id, :keyword, :category_code, :city, cast(:raw_json as jsonb))
            """
        ),
        rows,
    )
    db.commit()
    return len(rows)


def upsert_clean_poi(db: Session, poi: CleanPoi) -> str:
    update_result = db.execute(
        text(
            """
            update public.pois
            set category_code = :category_code,
                name_zh = :name_zh,
                name_en = :name_en,
                amap_type = :amap_type,
                amap_type_code = :amap_type_code,
                address = :address,
                district = :district,
                city = :city,
                province = :province,
                longitude = :longitude,
                latitude = :latitude,
                geom = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                amap_longitude = :amap_longitude,
                amap_latitude = :amap_latitude,
                rating = :rating,
                popularity_score = :popularity_score,
                tags = :tags,
                source = 'amap',
                source_raw = cast(:source_raw as jsonb),
                is_active = true,
                updated_at = now()
            where amap_poi_id = :amap_poi_id
            """
        ),
        _poi_params(poi),
    )
    if update_result.rowcount:
        return "updated"

    db.execute(
        text(
            """
            insert into public.pois (
                category_code, name_zh, name_en, amap_poi_id, amap_type, amap_type_code,
                address, district, city, province, longitude, latitude, geom,
                amap_longitude, amap_latitude, rating, popularity_score, tags, source, source_raw, is_active
            )
            values (
                :category_code, :name_zh, :name_en, :amap_poi_id, :amap_type, :amap_type_code,
                :address, :district, :city, :province, :longitude, :latitude,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                :amap_longitude, :amap_latitude, :rating, :popularity_score, :tags, 'amap', cast(:source_raw as jsonb), true
            )
            """
        ),
        _poi_params(poi),
    )
    return "inserted"


def import_clean_pois(db: Session, pois: list[CleanPoi]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for poi in pois:
        result = upsert_clean_poi(db, poi)
        if result == "inserted":
            inserted += 1
        else:
            updated += 1
    db.commit()
    return inserted, updated


def _poi_params(poi: CleanPoi) -> dict[str, Any]:
    return {
        "category_code": poi.category_code,
        "name_zh": poi.name_zh,
        "name_en": poi.name_en,
        "amap_poi_id": poi.amap_poi_id,
        "amap_type": poi.amap_type,
        "amap_type_code": poi.amap_type_code,
        "address": poi.address,
        "district": poi.district,
        "city": poi.city,
        "province": poi.province,
        "longitude": poi.longitude,
        "latitude": poi.latitude,
        "amap_longitude": poi.amap_longitude,
        "amap_latitude": poi.amap_latitude,
        "rating": poi.rating,
        "popularity_score": poi.popularity_score,
        "tags": poi.tags,
        "source_raw": json.dumps(poi.source_raw, ensure_ascii=False),
    }
