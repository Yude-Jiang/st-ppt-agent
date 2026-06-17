"""GCS storage for GeneratedDeck .pptx files, with local dev fallback."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

GCS_BUCKET = os.getenv("GCS_BUCKET", "st-ppt-agent-decks")
TTL_DAYS = 7
_LOCAL_DIR = Path("/tmp/st-ppt-agent-decks")


def upload_deck(task_id: str, pptx_bytes: bytes) -> tuple[str, str, datetime]:
    """Upload .pptx to GCS. Returns (gcs_path, download_url, expires_at).

    Falls back to local file + /api/tasks/{id}/download URL when GCS creds absent.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)
    blob_name = f"decks/{task_id}.pptx"
    gcs_path = f"gs://{GCS_BUCKET}/{blob_name}"

    try:
        from google.cloud import storage as gcs  # type: ignore
        client = gcs.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            pptx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".presentationml.presentation"
            ),
        )
        signed_url = blob.generate_signed_url(
            expiration=expires_at, method="GET", version="v4"
        )
        logger.info("uploaded deck task_id=%s gcs_path=%s", task_id, gcs_path)
        return gcs_path, signed_url, expires_at
    except Exception as e:
        logger.warning("GCS unavailable (%s), local fallback task_id=%s", type(e).__name__, task_id)
        _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        (_LOCAL_DIR / f"{task_id}.pptx").write_bytes(pptx_bytes)
        # Return a relative API URL that the download endpoint serves
        download_url = f"/api/tasks/{task_id}/download"
        return gcs_path, download_url, expires_at
