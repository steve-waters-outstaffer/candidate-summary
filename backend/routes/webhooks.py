"""RecruitCRM webhook endpoints."""

import threading
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, jsonify, request
import structlog

from helpers.ai_helpers import generate_html_summary, upload_resume_to_gemini
from helpers.recruitcrm_helpers import (
    fetch_candidate_interview_id,
    fetch_recruitcrm_candidate,
    fetch_recruitcrm_candidate_job_specific_fields,
    fetch_recruitcrm_job,
    fetch_alpharun_interview,
    push_to_recruitcrm_internal,
)

log = structlog.get_logger()

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.route("/webhooks/recruitcrm", methods=["POST"])
def recruitcrm_webhook() -> Any:
    """Handle RecruitCRM webhook callbacks."""
    payload = request.get_json(silent=True) or {}
    event = payload.get("event")
    data = payload.get("data") or {}
    candidate_slug = data.get("candidate_slug")
    job_slug = data.get("job_slug")

    log.info(
        "webhooks.recruitcrm.received",
        event=event,
        candidate_slug=candidate_slug,
        job_slug=job_slug,
    )

    app = current_app._get_current_object()
    worker = threading.Thread(
        target=_process_recruitcrm_payload,
        args=(app, payload),
        daemon=True,
        name="recruitcrm-webhook-worker",
    )
    worker.start()

    return jsonify({"status": "accepted"}), 200


def _process_recruitcrm_payload(app, payload: Dict[str, Any]) -> None:
    """Process the webhook payload within an application context."""
    with app.app_context():
        try:
            event = payload.get("event")
            data = payload.get("data") or {}
            candidate_slug = data.get("candidate_slug")
            job_slug = data.get("job_slug")

            if not candidate_slug or not job_slug:
                log.error(
                    "webhooks.recruitcrm.missing_slugs",
                    event=event,
                    candidate_slug=candidate_slug,
                    job_slug=job_slug,
                )
                return

            if not _is_stage_three_event(event, data):
                log.info(
                    "webhooks.recruitcrm.skipped",
                    reason="not_stage_three",
                    event=event,
                    candidate_slug=candidate_slug,
                    job_slug=job_slug,
                )
                return

            candidate_data = fetch_recruitcrm_candidate(candidate_slug)
            job_data = fetch_recruitcrm_job(job_slug, include_custom_fields=True)

            if not candidate_data or not job_data:
                log.error(
                    "webhooks.recruitcrm.fetch_failed",
                    candidate_found=bool(candidate_data),
                    job_found=bool(job_data),
                    candidate_slug=candidate_slug,
                    job_slug=job_slug,
                )
                return

            _merge_job_specific_fields(candidate_data, candidate_slug, job_slug)

            interview_data = _fetch_interview_data(candidate_slug, job_slug, job_data)
            client = current_app.client

            candidate_details = candidate_data.get("data", candidate_data)
            resume_info = candidate_details.get("resume")
            gemini_resume_file = None
            if resume_info and client:
                gemini_resume_file = upload_resume_to_gemini(resume_info, client)

            prompt_type = data.get("prompt_type", "recruitment.detailed")
            additional_context = data.get("additional_context", "")

            html_summary = generate_html_summary(
                candidate_data,
                job_data,
                interview_data,
                additional_context,
                prompt_type,
                None,
                gemini_resume_file,
                client,
            )

            if not html_summary:
                log.error(
                    "webhooks.recruitcrm.summary_failed",
                    candidate_slug=candidate_slug,
                    job_slug=job_slug,
                )
                return

            html_summary_with_note = _append_stage_three_note(html_summary)
            success = push_to_recruitcrm_internal(candidate_slug, html_summary_with_note)

            log.info(
                "webhooks.recruitcrm.push_complete",
                candidate_slug=candidate_slug,
                job_slug=job_slug,
                success=success,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            log.error("webhooks.recruitcrm.worker_exception", error=str(exc), exc_info=True)


def _is_stage_three_event(event: Optional[str], data: Dict[str, Any]) -> bool:
    """Validate that the webhook corresponds to a Stage 3 transition."""
    stage_payload = data.get("stage")

    stage_identifiers = [
        data.get("stage_id"),
        data.get("pipeline_stage_id"),
    ]
    stage_names = [data.get("stage_name"), data.get("stage_label")]

    if isinstance(stage_payload, dict):
        stage_identifiers.extend([
            stage_payload.get("id"),
            stage_payload.get("stage_id"),
        ])
        stage_names.extend([
            stage_payload.get("name"),
            stage_payload.get("label"),
        ])
    elif isinstance(stage_payload, str):
        stage_names.append(stage_payload)

    stage_identifiers = [value for value in stage_identifiers if value is not None]
    stage_names = [value for value in stage_names if isinstance(value, str)]

    for identifier in stage_identifiers:
        try:
            if int(identifier) == 3:
                return True
        except (TypeError, ValueError):
            continue

    normalized_names = {
        name.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
        for name in stage_names
    }
    if "stage3" in normalized_names:
        return True

    if event and isinstance(event, str) and "stage" in event.lower() and "3" in event:
        return True

    return False


def _merge_job_specific_fields(candidate_data: Dict[str, Any], candidate_slug: str, job_slug: str) -> None:
    """Merge job-specific custom fields into the candidate payload for prompt generation."""
    job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug)
    if not job_specific_fields:
        return

    candidate_details = candidate_data.setdefault("data", candidate_data)
    custom_fields = candidate_details.get("custom_fields") or []

    # Ensure we are working with a list copy before extending
    custom_fields = list(custom_fields)
    custom_fields.extend(field for field in job_specific_fields.values() if isinstance(field, dict))
    candidate_details["custom_fields"] = custom_fields


def _fetch_interview_data(candidate_slug: str, job_slug: str, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Attempt to fetch AlphaRun interview data for the candidate/job pair."""
    job_details = job_data.get("data", job_data)
    alpharun_job_id = None

    for field in job_details.get("custom_fields", []):
        if isinstance(field, dict) and field.get("field_name") == "AI Job ID":
            alpharun_job_id = field.get("value")
            break

    if not alpharun_job_id:
        return None

    interview_id = fetch_candidate_interview_id(candidate_slug, job_slug)
    if not interview_id:
        return None

    return fetch_alpharun_interview(alpharun_job_id, interview_id)


def _append_stage_three_note(summary: str) -> str:
    """Append an explanatory note to the generated summary."""
    note = (
        "<p><em>Generated automatically after the candidate reached Stage 3 in the "
        "RecruitCRM pipeline.</em></p>"
    )
    return f"{summary}\n{note}"
