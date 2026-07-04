from __future__ import annotations

import csv
import mimetypes
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session
from supabase import Client, create_client

from app.core.config import settings
from app.data_pipeline.import_pois import create_pipeline_engine, create_session


DEFAULT_CSV_PATH = Path("data/scenic_profiles/scenic_profiles.csv")
DEFAULT_BUCKET = "poi-images"


@dataclass
class ScenicProfileRow:
    amap_poi_id: str
    name_zh: str | None = None
    name_en: str | None = None
    short_intro_zh: str | None = None
    full_description_zh: str | None = None
    recommended_duration_minutes: int | None = None
    opening_hours: str | None = None
    ticket_info: str | None = None
    image_path: str | None = None
    image_caption: str | None = None


@dataclass
class ScenicProfileImportReport:
    csv_path: str
    total_rows: int = 0
    matched_pois: int = 0
    missing_pois: int = 0
    profiles_inserted: int = 0
    profiles_updated: int = 0
    images_inserted: int = 0
    images_updated: int = 0
    images_uploaded: int = 0
    url_images_used: int = 0
    skipped_images: int = 0
    errors: list[str] = field(default_factory=list)


def import_scenic_profiles_from_csv(
    csv_path: str | Path = DEFAULT_CSV_PATH,
    bucket: str = DEFAULT_BUCKET,
    dry_run: bool = False,
) -> ScenicProfileImportReport:
    resolved_csv_path = Path(csv_path)
    if not resolved_csv_path.is_absolute():
        resolved_csv_path = Path.cwd() / resolved_csv_path
    resolved_csv_path = resolved_csv_path.resolve()
    report = ScenicProfileImportReport(csv_path=str(resolved_csv_path))

    rows = read_scenic_profile_csv(resolved_csv_path)
    report.total_rows = len(rows)

    if dry_run:
        engine = create_pipeline_engine()
        db = create_session(engine)
        try:
            for row in rows:
                poi = find_poi_by_amap_id(db, row.amap_poi_id)
                if poi:
                    report.matched_pois += 1
                else:
                    report.missing_pois += 1
                    report.errors.append(f"Missing POI for amap_poi_id={row.amap_poi_id}")
                image_ref = resolve_image_reference(resolved_csv_path.parent, row.image_path, row.name_zh)
                if image_ref is None:
                    report.skipped_images += 1
                    report.errors.append(f"No image reference for amap_poi_id={row.amap_poi_id}, name_zh={row.name_zh}")
                    continue
                if image_ref["kind"] == "missing":
                    report.skipped_images += 1
                    report.errors.append(f"Missing image file for amap_poi_id={row.amap_poi_id}: {row.image_path}")
            return report
        finally:
            db.close()

    engine = create_pipeline_engine()
    db = create_session(engine)
    storage_client = create_storage_client()

    try:
        for row in rows:
            poi = find_poi_by_amap_id(db, row.amap_poi_id)
            if not poi:
                report.missing_pois += 1
                report.errors.append(f"Missing POI for amap_poi_id={row.amap_poi_id}")
                continue

            report.matched_pois += 1
            profile_result = upsert_scenic_profile(db, poi, row)
            if profile_result == "inserted":
                report.profiles_inserted += 1
            else:
                report.profiles_updated += 1

            image_result = handle_image(db, storage_client, bucket, resolved_csv_path.parent, poi, row)
            if image_result == "inserted":
                report.images_inserted += 1
            elif image_result == "updated":
                report.images_updated += 1
            elif image_result == "uploaded_inserted":
                report.images_uploaded += 1
                report.images_inserted += 1
            elif image_result == "uploaded_updated":
                report.images_uploaded += 1
                report.images_updated += 1
            elif image_result == "url_inserted":
                report.url_images_used += 1
                report.images_inserted += 1
            elif image_result == "url_updated":
                report.url_images_used += 1
                report.images_updated += 1
            elif image_result == "skipped":
                report.skipped_images += 1

        db.commit()
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def read_scenic_profile_csv(csv_path: Path) -> list[ScenicProfileRow]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")

    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return _read_scenic_profile_csv_with_encoding(csv_path, encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        last_error.encoding if last_error else "unknown",
        last_error.object if last_error else b"",
        last_error.start if last_error else 0,
        last_error.end if last_error else 0,
        f"CSV encoding is not supported: {csv_path}",
    )


def _read_scenic_profile_csv_with_encoding(csv_path: Path, encoding: str) -> list[ScenicProfileRow]:
    rows: list[ScenicProfileRow] = []
    with csv_path.open("r", encoding=encoding, newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or "amap_poi_id" not in reader.fieldnames:
            raise ValueError("CSV must contain header field: amap_poi_id")

        for index, raw_row in enumerate(reader, start=2):
            amap_poi_id = clean_text(raw_row.get("amap_poi_id"))
            if not amap_poi_id:
                raise ValueError(f"Row {index} missing required amap_poi_id")
            rows.append(
                ScenicProfileRow(
                    amap_poi_id=amap_poi_id,
                    name_zh=clean_text(raw_row.get("name_zh")),
                    name_en=clean_text(raw_row.get("name_en")),
                    short_intro_zh=clean_text(raw_row.get("short_intro_zh")),
                    full_description_zh=clean_text(raw_row.get("full_description_zh")),
                    recommended_duration_minutes=parse_optional_int(raw_row.get("recommended_duration_minutes"), index),
                    opening_hours=clean_text(raw_row.get("opening_hours")),
                    ticket_info=clean_text(raw_row.get("ticket_info")),
                    image_path=clean_text(raw_row.get("image_path")),
                    image_caption=clean_text(raw_row.get("image_caption")),
                )
            )

    return rows


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_optional_int(value: Any, row_index: int) -> int | None:
    text_value = clean_text(value)
    if text_value is None:
        return None
    try:
        return int(text_value)
    except ValueError as exc:
        raise ValueError(f"Row {row_index} recommended_duration_minutes must be an integer") from exc


def find_poi_by_amap_id(db: Session, amap_poi_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            select id::text, name_zh
            from public.pois
            where amap_poi_id = :amap_poi_id
              and category_code = 'scenic_spot'
            limit 1
            """
        ),
        {"amap_poi_id": amap_poi_id},
    ).mappings().first()
    return dict(row) if row else None


def upsert_scenic_profile(db: Session, poi: dict[str, Any], row: ScenicProfileRow) -> str:
    params = {
        "poi_id": poi["id"],
        "name_zh": row.name_zh or poi["name_zh"],
        "name_en": row.name_en,
        "short_intro_zh": row.short_intro_zh,
        "full_description_zh": row.full_description_zh,
        "recommended_duration_minutes": row.recommended_duration_minutes,
        "opening_hours": row.opening_hours,
        "ticket_info": row.ticket_info,
    }
    update_result = db.execute(
        text(
            """
            update public.scenic_spot_profiles
            set name_zh = :name_zh,
                name_en = :name_en,
                short_intro_zh = :short_intro_zh,
                full_description_zh = :full_description_zh,
                recommended_duration_minutes = :recommended_duration_minutes,
                opening_hours = :opening_hours,
                ticket_info = :ticket_info,
                updated_at = now()
            where poi_id = cast(:poi_id as uuid)
            """
        ),
        params,
    )
    if update_result.rowcount:
        return "updated"

    db.execute(
        text(
            """
            insert into public.scenic_spot_profiles (
                poi_id, name_zh, name_en, short_intro_zh, full_description_zh,
                recommended_duration_minutes, opening_hours, ticket_info
            )
            values (
                cast(:poi_id as uuid), :name_zh, :name_en, :short_intro_zh, :full_description_zh,
                :recommended_duration_minutes, :opening_hours, :ticket_info
            )
            """
        ),
        params,
    )
    return "inserted"


def handle_image(
    db: Session,
    storage_client: Client,
    bucket: str,
    csv_dir: Path,
    poi: dict[str, Any],
    row: ScenicProfileRow,
) -> str:
    image_ref = resolve_image_reference(csv_dir, row.image_path, row.name_zh)
    if image_ref is None:
        # Optional image: keep profile import successful even when no local image can be inferred.
        return "skipped"
    if image_ref["kind"] == "missing":
        return "skipped"

    caption = row.image_caption or row.name_zh
    if image_ref["kind"] == "url":
        result = upsert_poi_image(db, poi["id"], image_ref["url"], None, caption, "external_url")
        return f"url_{result}"

    storage_path = build_storage_path(poi["id"], image_ref["path"])
    image_url = upload_image(storage_client, bucket, image_ref["path"], storage_path)
    result = upsert_poi_image(db, poi["id"], image_url, storage_path, caption, "manual_upload")
    return f"uploaded_{result}"


def resolve_image_reference(csv_dir: Path, image_path: str | None, name_zh: str | None = None) -> dict[str, Any] | None:
    if not image_path:
        inferred = infer_image_path(csv_dir, name_zh)
        if inferred is None:
            return None
        return {"kind": "file", "path": inferred}
    parsed = urlparse(image_path)
    if parsed.scheme in {"http", "https"}:
        return {"kind": "url", "url": image_path}

    path = Path(image_path)
    if not path.is_absolute():
        path = csv_dir / path
    path = path.resolve()
    if not path.exists():
        return {"kind": "missing", "path": path}
    return {"kind": "file", "path": path}


def infer_image_path(csv_dir: Path, name_zh: str | None) -> Path | None:
    if not name_zh:
        return None
    images_dir = csv_dir / "images"
    if not images_dir.exists():
        return None

    supported_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    normalized_name = normalize_filename_stem(name_zh)
    for image_file in images_dir.iterdir():
        if not image_file.is_file() or image_file.suffix.lower() not in supported_suffixes:
            continue
        if image_file.stem == name_zh or normalize_filename_stem(image_file.stem) == normalized_name:
            return image_file.resolve()
    return None


def normalize_filename_stem(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


def build_storage_path(poi_id: str, image_path: Path) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", image_path.stem).strip("_") or "image"
    extension = image_path.suffix.lower() or ".jpg"
    return f"scenic/{poi_id}/{safe_name}{extension}"


def create_storage_client() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for local image upload")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def upload_image(client: Client, bucket: str, image_path: Path, storage_path: str) -> str:
    content_type = guess_image_content_type(image_path)
    with image_path.open("rb") as file:
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file,
            file_options={"content-type": content_type, "upsert": "true"},
        )
    return client.storage.from_(bucket).get_public_url(storage_path)


def guess_image_content_type(image_path: Path) -> str:
    suffix_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return suffix_map.get(image_path.suffix.lower()) or mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"


def upsert_poi_image(
    db: Session,
    poi_id: str,
    image_url: str,
    storage_path: str | None,
    caption: str | None,
    source: str,
) -> str:
    params = {
        "poi_id": poi_id,
        "image_url": image_url,
        "storage_path": storage_path,
        "caption_zh": caption,
        "source": source,
    }
    update_result = db.execute(
        text(
            """
            update public.poi_images
            set image_url = :image_url,
                storage_path = :storage_path,
                source = :source
            where poi_id = cast(:poi_id as uuid)
              and image_type = 'cover'
              and coalesce(caption_zh, '') = coalesce(:caption_zh, '')
            """
        ),
        params,
    )
    if update_result.rowcount:
        return "updated"

    db.execute(
        text(
            """
            insert into public.poi_images (
                poi_id, image_url, storage_path, image_type, caption_zh, source, sort_order
            )
            values (
                cast(:poi_id as uuid), :image_url, :storage_path, 'cover', :caption_zh, :source, 0
            )
            """
        ),
        params,
    )
    return "inserted"


def report_to_dict(report: ScenicProfileImportReport) -> dict[str, Any]:
    return asdict(report)
