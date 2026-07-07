import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.api.deps import (
    get_accessible_memberships,
    get_current_user,
    get_organization_membership,
    require_organization_manager,
    require_worker_context,
)
from app.api.v1.brand_lifecycle import ensure_brand_content_writable
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.content_versions import create_content_version_record, next_content_version_number
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.quality_checks import create_quality_check_record
from app.core.config import settings

from app.db.enums import GenerationType
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.content_item import ContentItem
from app.db.models.brand import Brand
from app.db.models.product import Product
from app.db.models.ticket import Ticket
from app.db.models.organization import Organization, OrganizationMembership
from app.db.session import get_db
from app.domain.content_generation import parse_content_generation_request
from app.domain.dna_generation import parse_dna_generation_request
from app.domain.ticket_processing import parse_ticket_processing_request
from app.domain.internal_agent_roles import resolve_internal_role_plan

from app.schemas.job import JobCreate, JobListResponse, JobRead
from app.schemas.job_lifecycle import JobCompleteRequest, JobFailureRequest, JobHeartbeatRequest
from app.storage import expected_artifact_key, read_job_artifact

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_brief_in_organization_brand(db: Session, brief_id: UUID, organization_id: UUID, brand_id: UUID) -> Brief:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    if brief.organization_id != organization_id or brief.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Brief does not belong to organization and brand")
    return brief


def _read_execution_trace(job: Job) -> dict | None:
    if not job.execution_trace_json:
        return None
    return json.loads(job.execution_trace_json)


def _read_internal_role_plan(job: Job) -> list[dict] | None:
    if not job.internal_role_plan_json:
        return None
    return json.loads(job.internal_role_plan_json)


def _write_internal_role_plan(job: Job, plan: list[dict] | None) -> None:
    job.internal_role_plan_json = json.dumps(plan) if plan is not None else None


def _resolved_internal_role_plan(job: Job) -> tuple[str, list[dict]]:
    persisted = _read_internal_role_plan(job)
    if persisted is not None:
        return job.execution_profile, persisted
    profile, plan = resolve_internal_role_plan(job.execution_profile)
    return profile, plan


def _legacy_completion_requests(brief: Brief | None) -> tuple[dict | None, dict | None, dict | None]:
    return (
        parse_content_generation_request(brief),
        parse_dna_generation_request(brief),
        parse_ticket_processing_request(brief),
    )


def _write_execution_trace(job: Job, trace: dict | None) -> None:
    job.execution_trace_json = json.dumps(trace) if trace is not None else None


def _base_scope(job: Job) -> dict:
    return {
        'organization_id': str(job.organization_id),
        'brand_id': str(job.brand_id),
        'brief_id': str(job.brief_id),
    }


def _ensure_execution_trace(job: Job) -> dict:
    trace = _read_execution_trace(job)
    if trace is None:
        trace = {
            'scope': _base_scope(job),
            'stage_history': [],
            'stage_timings': [],
            'events': [],
            'artifact_scope_status': None,
            'final_status': None,
            'failure_reason': None,
            'failure_stage': None,
            'failure_code': None,
            'validation_result': None,
            'last_progress': None,
            'progress_history': [],
            'stage_transition_counts': {},
            'dominant_stage_name': None,
            'stage_duration_ranking': [],
            'heartbeat_cadence_summary': None,
            'reclaim_continuity': None,
            'progress_extrema': None,
            'retry_profile': None,
            'worker_history': [],
            'transition_tag_rollup': [],
            'worker_metadata_key_summary': [],
            'stage_label_summary': {},
            'transition_tag_counts': {},
            'unique_transition_tag_count': 0,
            'progress_history_sample_count': 0,
            'latest_worker_metadata': None,
            'stage_label_history': {},
            'trace_compact_summary': None,
            'attempt_summary': None,
            'retry_reason': None,
        }
    else:
        trace.setdefault('scope', _base_scope(job))
        trace.setdefault('stage_history', [])
        trace.setdefault('stage_timings', [])
        trace.setdefault('events', [])
        trace.setdefault('artifact_scope_status', None)
        trace.setdefault('final_status', None)
        trace.setdefault('failure_reason', None)
        trace.setdefault('failure_stage', None)
        trace.setdefault('failure_code', None)
        trace.setdefault('validation_result', None)
        trace.setdefault('last_progress', None)
        trace.setdefault('progress_history', [])
        trace.setdefault('stage_transition_counts', {})
        trace.setdefault('dominant_stage_name', None)
        trace.setdefault('stage_duration_ranking', [])
        trace.setdefault('heartbeat_cadence_summary', None)
        trace.setdefault('reclaim_continuity', None)
        trace.setdefault('progress_extrema', None)
        trace.setdefault('retry_profile', None)
        trace.setdefault('worker_history', [])
        trace.setdefault('transition_tag_rollup', [])
        trace.setdefault('worker_metadata_key_summary', [])
        trace.setdefault('stage_label_summary', {})
        trace.setdefault('transition_tag_counts', {})
        trace.setdefault('unique_transition_tag_count', 0)
        trace.setdefault('progress_history_sample_count', 0)
        trace.setdefault('latest_worker_metadata', None)
        trace.setdefault('stage_label_history', {})
        trace.setdefault('trace_compact_summary', None)
        trace.setdefault('attempt_summary', None)
        trace.setdefault('retry_reason', None)
    return trace


def _append_stage(trace: dict, stage_name: str) -> None:
    stage_history = trace.setdefault('stage_history', [])
    stage_history.append(stage_name)
    counts = trace.setdefault('stage_transition_counts', {})
    counts[stage_name] = counts.get(stage_name, 0) + 1
    ranked = {name: count for name, count in counts.items() if name not in {'claimed', 'completed', 'failed'}}
    if ranked:
        trace['dominant_stage_name'] = max(ranked.items(), key=lambda item: item[1])[0]
    else:
        trace['dominant_stage_name'] = 'claimed' if counts.get('claimed') else None


def _isoformat_z(value: datetime) -> str:
    return value.isoformat().replace('+00:00', 'Z')


def _close_active_stage(trace: dict, at: datetime) -> None:
    stage_timings = trace.setdefault('stage_timings', [])
    if not stage_timings:
        return
    active = stage_timings[-1]
    if active.get('exited_at') is not None:
        return
    entered_at = datetime.fromisoformat(active['entered_at'].replace('Z', '+00:00'))
    active['exited_at'] = _isoformat_z(at)
    active['duration_seconds'] = max((at - entered_at).total_seconds(), 0.0)


def _begin_stage(trace: dict, stage_name: str, at: datetime) -> None:
    _close_active_stage(trace, at)
    trace.setdefault('stage_timings', []).append(
        {
            'stage_name': stage_name,
            'entered_at': _isoformat_z(at),
            'exited_at': None,
            'duration_seconds': None,
        }
    )


def _append_event(trace: dict, event_name: str, at: datetime, worker_id: str | None = None, **extra: object) -> None:
    events = trace.setdefault('events', [])
    payload = {
        'event': event_name,
        'at': _isoformat_z(at),
    }
    if worker_id is not None:
        payload['worker_id'] = worker_id
    payload.update({key: value for key, value in extra.items() if value is not None})
    events.append(payload)


def _trace_started_at(trace: dict) -> datetime | None:
    events = trace.get('events') or []
    if not events:
        return None
    claimed_at = events[0].get('at')
    if not claimed_at:
        return None
    return datetime.fromisoformat(claimed_at.replace('Z', '+00:00'))


def _terminal_event_metrics(trace: dict, finished_at: datetime) -> dict[str, object]:
    payload: dict[str, object] = {
        'stage_count': len(trace.get('stage_history') or []),
    }
    started_at = _trace_started_at(trace)
    if started_at is not None:
        payload['lifecycle_seconds'] = max((finished_at - started_at).total_seconds(), 0.0)
    return payload


def _artifact_trace_snapshot(payload: JobCompleteRequest | None) -> dict[str, object] | None:
    if payload is None or payload.output_artifact_key is None:
        return None
    return {
        'key': payload.output_artifact_key,
        'url': payload.output_artifact_url,
        'content_type': payload.output_artifact_content_type,
        'size_bytes': payload.output_artifact_size_bytes,
        'etag': payload.output_artifact_etag,
    }


def _validation_result_snapshot(
    status: str,
    *,
    artifact_scope_status: str | None = None,
    artifact_key: str | None = None,
    reason: str | None = None,
    failure_code: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {'status': status}
    if artifact_scope_status is not None:
        result['artifact_scope_status'] = artifact_scope_status
    if artifact_key is not None:
        result['artifact_key'] = artifact_key
    if reason is not None:
        result['reason'] = reason
    if failure_code is not None:
        result['failure_code'] = failure_code
    return result


def _current_failure_stage(trace: dict) -> str | None:
    stage_history = trace.get('stage_history') or []
    for stage_name in reversed(stage_history):
        if stage_name not in {'failed', 'completed'}:
            return stage_name
    return None


def _classify_failure_code(error_message: str) -> str:
    message = error_message.lower()
    if 'artifact key escaped job scope' in message:
        return 'artifact_scope_rejection'
    if 'timeout' in message and 'upstream' in message:
        return 'upstream_timeout'
    return 'unknown_failure'


def _progress_snapshot(payload: JobHeartbeatRequest | None) -> dict[str, object] | None:
    if payload is None or payload.stage_name is None:
        return None
    snapshot = {
        'stage_name': payload.stage_name,
        'stage_label': payload.stage_label,
        'progress_percent': payload.progress_percent,
        'progress_message': payload.progress_message,
        'transition_tag': payload.transition_tag,
        'worker_metadata': payload.worker_metadata,
    }
    return {key: value for key, value in snapshot.items() if value is not None}


def _next_progress_sequence(trace: dict) -> int:
    last_progress = trace.get('last_progress') or {}
    value = last_progress.get('progress_sequence')
    return value + 1 if isinstance(value, int) else 1


def _attempt_scoped_progress_snapshot(trace: dict, payload: JobHeartbeatRequest, attempt_number: int) -> dict[str, object]:
    snapshot = _progress_snapshot(payload) or {}
    snapshot['attempt_number'] = attempt_number
    snapshot['progress_sequence'] = _next_progress_sequence(trace)
    previous_progress = trace.get('last_progress') or {}
    current_percent = snapshot.get('progress_percent')
    previous_percent = previous_progress.get('progress_percent')
    if isinstance(current_percent, int):
        if isinstance(previous_percent, int):
            snapshot['progress_delta_percent'] = current_percent - previous_percent
        else:
            snapshot['progress_delta_percent'] = current_percent
    return snapshot


def _attempt_summary(trace: dict) -> dict[str, object] | None:
    last_progress = trace.get('last_progress')
    if not isinstance(last_progress, dict):
        return None
    started_at = _trace_started_at(trace)
    duration_seconds = None
    if started_at is not None:
        events = trace.get('events') or []
        last_progress_event_at = None
        for event in reversed(events):
            if event.get('event') == 'heartbeat':
                last_progress_event_at = event.get('at')
                break
        if last_progress_event_at:
            current_at = datetime.fromisoformat(last_progress_event_at.replace('Z', '+00:00'))
            duration_seconds = max((current_at - started_at).total_seconds(), 0.0)
    progress_history = trace.get('progress_history') or []
    progress_event_count = len(progress_history)
    last_stage_name = last_progress.get('stage_name')
    repeat_count = 0
    if last_stage_name is not None:
        for item in reversed(progress_history):
            if item.get('stage_name') == last_stage_name:
                repeat_count += 1
            else:
                break
    percents = [item.get('progress_percent') for item in progress_history if isinstance(item.get('progress_percent'), int)]
    sequences = [item.get('progress_sequence') for item in progress_history if isinstance(item.get('progress_sequence'), int)]
    deltas = [item.get('progress_delta_percent') for item in progress_history if isinstance(item.get('progress_delta_percent'), int)]
    stage_names = [item.get('stage_name') for item in progress_history if isinstance(item.get('stage_name'), str)]
    last_progress_percent = last_progress.get('progress_percent')
    first_progress_percent = percents[0] if percents else None
    min_progress_percent = min(percents) if percents else None
    max_progress_percent = max(percents) if percents else None
    return {
        'attempt_number': last_progress.get('attempt_number'),
        'progress_event_count': progress_event_count,
        'last_stage_name': last_stage_name,
        'last_stage_label': last_progress.get('stage_label'),
        'last_progress_percent': last_progress_percent,
        'last_progress_sequence': last_progress.get('progress_sequence'),
        'attempt_duration_seconds': duration_seconds,
        'progress_velocity_percent_per_second': (
            last_progress_percent / duration_seconds
            if isinstance(last_progress_percent, int) and isinstance(duration_seconds, float) and duration_seconds > 0
            else None
        ),
        'attempt_completion_ratio': (
            round(last_progress_percent / 100, 4)
            if isinstance(last_progress_percent, int)
            else None
        ),
        'last_stage_repeat_count': repeat_count,
        'attempt_event_density_per_second': (
            progress_event_count / duration_seconds
            if isinstance(duration_seconds, float) and duration_seconds > 0
            else None
        ),
        'progress_remaining_percent': (
            100 - last_progress_percent
            if isinstance(last_progress_percent, int)
            else None
        ),
        'first_progress_percent': first_progress_percent,
        'first_stage_label': progress_history[0].get('stage_label') if progress_history else None,
        'first_transition_tag': progress_history[0].get('transition_tag') if progress_history else None,
        'min_progress_percent': min_progress_percent,
        'max_progress_percent': max_progress_percent,
        'unique_stage_count': len(set(stage_names)),
        'unique_transition_tag_count': trace.get('unique_transition_tag_count'),
        'worker_metadata_key_count': len(trace.get('worker_metadata_key_summary') or []),
        'transition_tag_total_count': len(trace.get('transition_tag_rollup') or []),
        'latest_worker_metadata_keys': sorted((trace.get('latest_worker_metadata') or {}).keys()),
        'latest_transition_tag': last_progress.get('transition_tag'),
        'progress_sequence_span': (max(sequences) - min(sequences) + 1) if sequences else None,
        'total_progress_delta_percent': (
            last_progress_percent - first_progress_percent
            if isinstance(last_progress_percent, int) and isinstance(first_progress_percent, int)
            else None
        ),
        'average_progress_delta_percent': (sum(deltas) / len(deltas)) if deltas else None,
        'average_progress_percent': (sum(percents) / len(percents)) if percents else None,
    }


def _progress_extrema(trace: dict) -> dict[str, object] | None:
    progress_history = trace.get('progress_history') or []
    percents = [item.get('progress_percent') for item in progress_history if isinstance(item.get('progress_percent'), int)]
    if not percents:
        return None
    return {
        'min_progress_percent': min(percents),
        'max_progress_percent': max(percents),
        'progress_spread_percent': max(percents) - min(percents),
        'first_progress_percent': percents[0],
    }


def _retry_profile(trace: dict) -> dict[str, object]:
    claimed_events = [event for event in (trace.get('events') or []) if event.get('event') == 'claimed']
    latest_attempt_number = claimed_events[-1].get('attempt_number') if claimed_events else None
    latest_claim_type = claimed_events[-1].get('claim_type') if claimed_events else None
    reclaim_count = 0
    if isinstance(latest_attempt_number, int):
        reclaim_count = max(latest_attempt_number - 1, 0)
    elif any(event.get('claim_type') == 'reclaimed' for event in claimed_events):
        reclaim_count = 1
    return {
        'attempt_count': latest_attempt_number or 0,
        'reclaim_count': reclaim_count,
        'latest_attempt_number': latest_attempt_number,
        'current_claim_type': latest_claim_type,
    }


def _worker_recap(trace: dict) -> dict[str, object]:
    worker_history = trace.get('worker_history') or []
    reclaim_continuity = trace.get('reclaim_continuity') or {}
    retry_profile = trace.get('retry_profile') or {}
    return {
        'current_worker_id': worker_history[-1] if worker_history else None,
        'reclaimed_from_worker_id': reclaim_continuity.get('reclaimed_from_worker_id'),
        'worker_count': len(worker_history),
        'retry_reason': trace.get('retry_reason'),
        'current_claim_type': retry_profile.get('current_claim_type'),
        'had_reclaim': bool(reclaim_continuity),
        'reclaim_count': retry_profile.get('reclaim_count', 0),
        'attempt_count': retry_profile.get('attempt_count', 0),
        'latest_transition_tag': (trace.get('last_progress') or {}).get('transition_tag'),
        'latest_worker_metadata_keys': sorted((trace.get('latest_worker_metadata') or {}).keys()),
        'worker_metadata_key_count': len(trace.get('worker_metadata_key_summary') or []),
    }


def _transition_tag_rollup(trace: dict) -> list[str]:
    tags: list[str] = []
    for item in trace.get('progress_history') or []:
        tag = item.get('transition_tag')
        if isinstance(tag, str):
            tags.append(tag)
    return tags


def _worker_metadata_key_summary(trace: dict) -> list[str]:
    keys: set[str] = set()
    for item in trace.get('progress_history') or []:
        worker_metadata = item.get('worker_metadata')
        if isinstance(worker_metadata, dict):
            for key in worker_metadata.keys():
                if isinstance(key, str):
                    keys.add(key)
    return sorted(keys)


def _transition_tag_counts(trace: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in trace.get('progress_history') or []:
        tag = item.get('transition_tag')
        if isinstance(tag, str):
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _latest_worker_metadata(trace: dict) -> dict[str, object] | None:
    for item in reversed(trace.get('progress_history') or []):
        worker_metadata = item.get('worker_metadata')
        if isinstance(worker_metadata, dict):
            return worker_metadata
    return None


def _unique_transition_tag_count(trace: dict) -> int:
    return len(_transition_tag_counts(trace))


def _progress_history_sample_count(trace: dict) -> int:
    return len(trace.get('progress_history') or [])


def _stage_label_summary(trace: dict) -> dict[str, str]:
    summary: dict[str, str] = {}
    for item in trace.get('progress_history') or []:
        stage_name = item.get('stage_name')
        stage_label = item.get('stage_label')
        if isinstance(stage_name, str) and isinstance(stage_label, str):
            summary[stage_name] = stage_label
    return summary


def _stage_label_history(trace: dict) -> dict[str, list[str]]:
    history: dict[str, list[str]] = {}
    for item in trace.get('progress_history') or []:
        stage_name = item.get('stage_name')
        stage_label = item.get('stage_label')
        if not isinstance(stage_name, str) or not isinstance(stage_label, str):
            continue
        bucket = history.setdefault(stage_name, [])
        if not bucket or bucket[-1] != stage_label:
            bucket.append(stage_label)
    return history


def _stage_duration_ranking(trace: dict) -> list[dict[str, object]]:
    aggregates: dict[str, dict[str, float | int | str]] = {}
    for timing in trace.get('stage_timings') or []:
        stage_name = timing.get('stage_name')
        duration = timing.get('duration_seconds')
        if not isinstance(stage_name, str) or not isinstance(duration, (int, float)):
            continue
        bucket = aggregates.setdefault(stage_name, {
            'stage_name': stage_name,
            'total_duration_seconds': 0.0,
            'transition_count': 0,
        })
        bucket['total_duration_seconds'] = float(bucket['total_duration_seconds']) + float(duration)
        bucket['transition_count'] = int(bucket['transition_count']) + 1
    ranking: list[dict[str, object]] = []
    for bucket in aggregates.values():
        total = float(bucket['total_duration_seconds'])
        count = int(bucket['transition_count'])
        ranking.append({
            'stage_name': bucket['stage_name'],
            'total_duration_seconds': total,
            'transition_count': count,
            'average_duration_seconds': (total / count) if count > 0 else 0.0,
        })
    ranking.sort(key=lambda item: item['total_duration_seconds'], reverse=True)
    return ranking


def _heartbeat_cadence_summary(trace: dict) -> dict[str, object] | None:
    heartbeats = [event for event in (trace.get('events') or []) if event.get('event') == 'heartbeat']
    if not heartbeats:
        return None
    if len(heartbeats) == 1:
        return {
            'heartbeat_count': 1,
            'average_gap_seconds': None,
            'max_gap_seconds': None,
        }
    times = [datetime.fromisoformat(event['at'].replace('Z', '+00:00')) for event in heartbeats]
    gaps = [(curr - prev).total_seconds() for prev, curr in zip(times, times[1:])]
    return {
        'heartbeat_count': len(heartbeats),
        'average_gap_seconds': sum(gaps) / len(gaps),
        'max_gap_seconds': max(gaps),
    }


def _reclaim_continuity(trace: dict) -> dict[str, object] | None:
    events = trace.get('events') or []
    if not events:
        return None
    claimed = events[0]
    if claimed.get('event') != 'claimed' or claimed.get('claim_type') != 'reclaimed':
        return None
    return {
        'claim_type': claimed.get('claim_type'),
        'reclaimed_from_worker_id': claimed.get('reclaimed_from_worker_id'),
        'retry_reason': claimed.get('retry_reason'),
        'attempt_number': claimed.get('attempt_number'),
    }


def _trace_compact_summary(trace: dict) -> dict[str, object]:
    attempt_summary = trace.get('attempt_summary') or {}
    stage_history = trace.get('stage_history') or []
    retry_profile = trace.get('retry_profile') or {}
    return {
        'current_stage': stage_history[-1] if stage_history else None,
        'final_status': trace.get('final_status'),
        'attempt_number': attempt_summary.get('attempt_number'),
        'dominant_stage_name': trace.get('dominant_stage_name'),
        'heartbeat_count': len([event for event in (trace.get('events') or []) if event.get('event') == 'heartbeat']),
        'reclaim_count': retry_profile.get('reclaim_count', 0),
        'has_progress': trace.get('last_progress') is not None,
        'progress_span_percent': (trace.get('progress_extrema') or {}).get('progress_spread_percent'),
        'last_stage_label': attempt_summary.get('last_stage_label'),
        'average_progress_percent': attempt_summary.get('average_progress_percent'),
        'unique_transition_tag_count': trace.get('unique_transition_tag_count'),
        'latest_transition_tag': attempt_summary.get('latest_transition_tag'),
        'first_transition_tag': attempt_summary.get('first_transition_tag'),
        'transition_tag_total_count': len(trace.get('transition_tag_rollup') or []),
        'progress_history_sample_count': trace.get('progress_history_sample_count'),
        'first_progress_percent': attempt_summary.get('first_progress_percent'),
        'unique_stage_count': attempt_summary.get('unique_stage_count'),
        'worker_count': len(trace.get('worker_history') or []),
        'worker_metadata_key_count': len(trace.get('worker_metadata_key_summary') or []),
        'latest_worker_metadata_keys': sorted((trace.get('latest_worker_metadata') or {}).keys()),
        'max_progress_percent': attempt_summary.get('max_progress_percent'),
        'stage_label_entry_count': len(trace.get('stage_label_summary') or {}),
    }


def _timeline_digest(trace: dict) -> dict[str, object]:
    heartbeat_count = len([event for event in (trace.get('events') or []) if event.get('event') == 'heartbeat'])
    progress_extrema = trace.get('progress_extrema') or {}
    progress_history = trace.get('progress_history') or []
    return {
        'stage_count': len(trace.get('stage_history') or []),
        'heartbeat_count': heartbeat_count,
        'latest_stage_name': _current_failure_stage(trace),
        'progress_span_percent': progress_extrema.get('progress_spread_percent'),
        'first_stage_name': progress_history[0].get('stage_name') if progress_history else None,
        'first_stage_label': progress_history[0].get('stage_label') if progress_history else None,
        'first_transition_tag': progress_history[0].get('transition_tag') if progress_history else None,
        'first_progress_percent': progress_history[0].get('progress_percent') if progress_history else None,
        'first_progress_sequence': progress_history[0].get('progress_sequence') if progress_history else None,
        'latest_stage_label': progress_history[-1].get('stage_label') if progress_history else None,
        'latest_transition_tag': progress_history[-1].get('transition_tag') if progress_history else None,
        'worker_metadata_key_count': len(trace.get('worker_metadata_key_summary') or []),
        'latest_worker_metadata_keys': sorted((progress_history[-1].get('worker_metadata') or {}).keys()) if progress_history else [],
        'latest_progress_percent': progress_history[-1].get('progress_percent') if progress_history else None,
        'last_progress_sequence': progress_history[-1].get('progress_sequence') if progress_history else None,
    }


def _scope_recap(trace: dict) -> dict[str, object]:
    return trace.get('scope') or {}


def _failure_digest(trace: dict) -> dict[str, object]:
    attempt_summary = trace.get('attempt_summary') or {}
    return {
        'failure_code': trace.get('failure_code'),
        'failure_stage': trace.get('failure_stage'),
        'had_progress': trace.get('last_progress') is not None,
        'attempt_number': attempt_summary.get('attempt_number'),
        'retry_reason': trace.get('retry_reason'),
        'progress_remaining_percent': attempt_summary.get('progress_remaining_percent'),
        'current_claim_type': (trace.get('retry_profile') or {}).get('current_claim_type'),
        'had_reclaim': bool(trace.get('reclaim_continuity')),
        'reclaim_count': (trace.get('retry_profile') or {}).get('reclaim_count', 0),
        'worker_count': len(trace.get('worker_history') or []),
        'latest_transition_tag': (trace.get('last_progress') or {}).get('transition_tag'),
        'latest_worker_metadata_keys': sorted((trace.get('latest_worker_metadata') or {}).keys()),
        'transition_tag_total_count': len(trace.get('transition_tag_rollup') or []),
        'attempt_completion_ratio': attempt_summary.get('attempt_completion_ratio'),
    }


def _refresh_trace_derived_fields(trace: dict) -> None:
    trace['stage_duration_ranking'] = _stage_duration_ranking(trace)
    trace['heartbeat_cadence_summary'] = _heartbeat_cadence_summary(trace)
    trace['reclaim_continuity'] = _reclaim_continuity(trace)
    trace['progress_extrema'] = _progress_extrema(trace)
    trace['retry_profile'] = _retry_profile(trace)
    trace['transition_tag_rollup'] = _transition_tag_rollup(trace)
    trace['transition_tag_counts'] = _transition_tag_counts(trace)
    trace['unique_transition_tag_count'] = _unique_transition_tag_count(trace)
    trace['progress_history_sample_count'] = _progress_history_sample_count(trace)
    trace['worker_metadata_key_summary'] = _worker_metadata_key_summary(trace)
    trace['latest_worker_metadata'] = _latest_worker_metadata(trace)
    trace['stage_label_summary'] = _stage_label_summary(trace)
    trace['stage_label_history'] = _stage_label_history(trace)
    trace['attempt_summary'] = _attempt_summary(trace)
    trace['trace_compact_summary'] = _trace_compact_summary(trace)


def _progress_window(trace: dict) -> dict[str, object] | None:
    attempt_summary = trace.get('attempt_summary') or {}
    if not attempt_summary:
        return None
    return {
        'first_progress_percent': attempt_summary.get('first_progress_percent'),
        'last_progress_percent': attempt_summary.get('last_progress_percent'),
        'min_progress_percent': attempt_summary.get('min_progress_percent'),
        'max_progress_percent': attempt_summary.get('max_progress_percent'),
        'progress_remaining_percent': attempt_summary.get('progress_remaining_percent'),
        'average_progress_percent': attempt_summary.get('average_progress_percent'),
        'total_progress_delta_percent': attempt_summary.get('total_progress_delta_percent'),
        'progress_span_percent': (trace.get('progress_extrema') or {}).get('progress_spread_percent'),
        'progress_sequence_span': attempt_summary.get('progress_sequence_span'),
    }


def _progress_digest(trace: dict) -> dict[str, object] | None:
    attempt_summary = trace.get('attempt_summary') or {}
    last_progress = trace.get('last_progress') or {}
    if not last_progress:
        return None
    return {
        'last_progress_percent': last_progress.get('progress_percent'),
        'last_progress_sequence': last_progress.get('progress_sequence'),
        'progress_event_count': attempt_summary.get('progress_event_count', 0),
        'dominant_stage_name': trace.get('dominant_stage_name'),
        'progress_velocity_percent_per_second': attempt_summary.get('progress_velocity_percent_per_second'),
        'total_progress_delta_percent': attempt_summary.get('total_progress_delta_percent'),
        'average_progress_delta_percent': attempt_summary.get('average_progress_delta_percent'),
        'average_progress_percent': attempt_summary.get('average_progress_percent'),
        'min_progress_percent': attempt_summary.get('min_progress_percent'),
        'max_progress_percent': attempt_summary.get('max_progress_percent'),
        'first_progress_percent': attempt_summary.get('first_progress_percent'),
        'progress_remaining_percent': attempt_summary.get('progress_remaining_percent'),
        'unique_transition_tag_count': attempt_summary.get('unique_transition_tag_count'),
        'latest_transition_tag': attempt_summary.get('latest_transition_tag'),
        'worker_metadata_key_count': attempt_summary.get('worker_metadata_key_count'),
    }


def _trace_summary(trace: dict) -> dict[str, object]:
    attempt_summary = trace.get('attempt_summary') or {}
    return {
        'final_status': trace.get('final_status'),
        'failure_code': trace.get('failure_code'),
        'stage_count': len(trace.get('stage_history') or []),
        'progress_event_count': attempt_summary.get('progress_event_count', 0),
        'attempt_number': attempt_summary.get('attempt_number'),
    }


def _job_read(job: Job) -> JobRead:
    execution_profile, internal_role_plan = _resolved_internal_role_plan(job)
    payload = {
        'id': job.id,
        'organization_id': job.organization_id,
        'brand_id': job.brand_id,
        'brief_id': job.brief_id,
        'kind': job.kind,
        'target_brand_id': job.target_brand_id,
        'target_product_id': job.target_product_id,
        'target_content_item_id': job.target_content_item_id,
        'target_ticket_id': job.target_ticket_id,
        'scope': _base_scope(job),
        'execution_profile': execution_profile,
        'internal_role_plan': internal_role_plan,
        'execution_trace': _ensure_execution_trace(job),
        'title': job.title,
        'status': job.status,
        'worker_id': job.worker_id,
        'attempt_count': job.attempt_count,
        'lease_expires_at': job.lease_expires_at,
        'started_at': job.started_at,
        'finished_at': job.finished_at,
        'error_message': job.error_message,
        'output_text': job.output_text,
        'output_artifact_key': job.output_artifact_key,
        'output_artifact_url': job.output_artifact_url,
        'output_artifact_content_type': job.output_artifact_content_type,
        'output_artifact_size_bytes': job.output_artifact_size_bytes,
        'output_artifact_etag': job.output_artifact_etag,
        'last_stage': job.last_stage,
        'last_heartbeat_at': job.last_heartbeat_at,
        'created_at': job.created_at,
        'updated_at': job.updated_at,
    }
    return JobRead.model_validate(payload)


def _get_job_or_404(db: Session, job_id: UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _lease_deadline() -> datetime:
    return _now() + timedelta(seconds=settings.worker_lease_seconds)


def _is_lease_stale(job: Job) -> bool:
    lease_expires_at = _normalize_dt(job.lease_expires_at)
    return lease_expires_at is not None and lease_expires_at <= _now()


def _claim_job(
    job: Job,
    worker_id: str,
    *,
    claim_type: str = 'claimed',
    reclaimed_from_worker_id: str | None = None,
) -> Job:
    now = _now()
    job.status = "running"
    job.worker_id = worker_id
    if job.started_at is None:
        job.started_at = now
    job.lease_expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
    job.attempt_count += 1
    job.finished_at = None
    job.error_message = None
    job.output_text = None
    job.output_artifact_key = None
    job.output_artifact_url = None
    job.output_artifact_content_type = None
    job.output_artifact_size_bytes = None
    job.output_artifact_etag = None
    trace = _ensure_execution_trace(job)
    trace['stage_history'] = ['claimed']
    trace['stage_timings'] = []
    trace['events'] = []
    trace['artifact_scope_status'] = None
    trace['final_status'] = None
    trace['failure_reason'] = None
    trace['failure_stage'] = None
    trace['failure_code'] = None
    trace['last_progress'] = None
    trace['progress_history'] = []
    trace['stage_transition_counts'] = {'claimed': 1}
    trace['dominant_stage_name'] = 'claimed'
    trace['stage_duration_ranking'] = []
    trace['heartbeat_cadence_summary'] = None
    trace['reclaim_continuity'] = None
    trace['progress_extrema'] = None
    trace['retry_profile'] = None
    trace['worker_history'] = [reclaimed_from_worker_id, worker_id] if reclaimed_from_worker_id is not None else [worker_id]
    trace['transition_tag_rollup'] = []
    trace['transition_tag_counts'] = {}
    trace['unique_transition_tag_count'] = 0
    trace['progress_history_sample_count'] = 0
    trace['worker_metadata_key_summary'] = []
    trace['latest_worker_metadata'] = None
    trace['stage_label_summary'] = {}
    trace['stage_label_history'] = {}
    trace['trace_compact_summary'] = None
    trace['attempt_summary'] = None
    trace['retry_reason'] = 'lease_expired' if claim_type == 'reclaimed' else None
    _begin_stage(trace, 'claimed', now)
    _append_event(
        trace,
        'claimed',
        now,
        worker_id=worker_id,
        claim_type=claim_type,
        attempt_number=job.attempt_count,
        reclaimed_from_worker_id=reclaimed_from_worker_id,
        retry_reason=trace['retry_reason'],
    )
    _refresh_trace_derived_fields(trace)
    _write_execution_trace(job, trace)
    job.last_stage = 'claimed'
    job.last_heartbeat_at = now
    return job


def _require_job_owned_by_worker(job: Job, worker_id: str) -> None:
    if job.worker_id != worker_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is owned by another worker")


def _require_active_owner_lease(job: Job, worker_id: str) -> None:
    _require_job_owned_by_worker(job, worker_id)
    if _is_lease_stale(job):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job lease expired or job was reclaimed by another worker",
        )


@router.post("/claim-next", response_model=JobRead)
def claim_next_job(
    worker_id: str = Depends(require_worker_context),
    db: Session = Depends(get_db),
) -> JobRead:
    now = _now()
    job = db.execute(
        select(Job)
        .where(or_(Job.status == "queued", (Job.status == "running") & (Job.lease_expires_at.is_not(None)) & (Job.lease_expires_at <= now)))
        .order_by(Job.created_at.asc())
    ).scalars().first()
    if job is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    previous_worker_id = job.worker_id if job.status == 'running' else None
    claim_type = 'reclaimed' if previous_worker_id is not None else 'claimed'
    _claim_job(job, worker_id, claim_type=claim_type, reclaimed_from_worker_id=previous_worker_id)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    brief_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    get_brief_in_organization_brand(db, brief_id, organization_id, brand_id)
    items = db.execute(
        select(Job)
        .where(Job.organization_id == organization_id, Job.brand_id == brand_id, Job.brief_id == brief_id)
        .order_by(Job.created_at.asc())
    ).scalars().all()
    return JobListResponse(items=[_job_read(item) for item in items])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    brand = get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    ensure_brand_content_writable(brand)
    get_brief_in_organization_brand(db, payload.brief_id, payload.organization_id, payload.brand_id)
    execution_profile, internal_role_plan = resolve_internal_role_plan(payload.execution_profile)
    job = Job(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        brief_id=payload.brief_id,
        title=payload.title,
        status="queued",
        execution_profile=execution_profile,
        kind=payload.kind or 'manual',
        target_brand_id=payload.target_brand_id,
        target_product_id=payload.target_product_id,
        target_content_item_id=payload.target_content_item_id,
        target_ticket_id=payload.target_ticket_id,
    )
    _write_internal_role_plan(job, internal_role_plan)
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, job_id)
    get_organization_membership(job.organization_id, memberships)
    return _job_read(job)


@router.get("/{job_id}/artifact")
def get_job_artifact(
    job_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> Response:
    job = _get_job_or_404(db, job_id)
    get_organization_membership(job.organization_id, memberships)
    payload, content_type = read_job_artifact(settings, job)
    return Response(content=payload, media_type=content_type)


@router.post("/{job_id}/claim", response_model=JobRead)
def claim_job(
    job_id: UUID,
    worker_id: str = Depends(require_worker_context),
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, job_id)
    if job.status != "queued":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not claimable")
    _claim_job(job, worker_id)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.post("/{job_id}/heartbeat", response_model=JobRead)
def heartbeat_job(
    job_id: UUID,
    payload: JobHeartbeatRequest | None = None,
    worker_id: str = Depends(require_worker_context),
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, job_id)
    if job.status != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not running")
    _require_job_owned_by_worker(job, worker_id)
    now = _now()
    job.lease_expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
    job.last_heartbeat_at = now
    if payload is not None and payload.stage_name:
        job.last_stage = payload.stage_name
        trace = _ensure_execution_trace(job)
        progress_snapshot = _attempt_scoped_progress_snapshot(trace, payload, job.attempt_count)
        trace['last_progress'] = progress_snapshot
        trace.setdefault('progress_history', []).append(progress_snapshot)
        _append_stage(trace, payload.stage_name)
        _begin_stage(trace, payload.stage_name, now)
        _append_event(
            trace,
            'heartbeat',
            now,
            worker_id=worker_id,
            stage_name=payload.stage_name,
            stage_label=payload.stage_label,
            progress_percent=payload.progress_percent,
            progress_message=payload.progress_message,
            transition_tag=payload.transition_tag,
            worker_metadata=payload.worker_metadata,
            attempt_number=progress_snapshot['attempt_number'],
            progress_sequence=progress_snapshot['progress_sequence'],
            progress_delta_percent=progress_snapshot.get('progress_delta_percent'),
        )
        _refresh_trace_derived_fields(trace)
        _write_execution_trace(job, trace)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.post("/{job_id}/complete", response_model=JobRead)
def complete_job(
    job_id: UUID,
    payload: JobCompleteRequest | None = None,
    worker_id: str = Depends(require_worker_context),
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, job_id)
    if job.status != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not running")
    _require_active_owner_lease(job, worker_id)
    artifact_key = payload.output_artifact_key if payload is not None else None
    if artifact_key is not None and artifact_key != expected_artifact_key(job):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Completed artifact key is outside the job tenant namespace',
        )
    now = _now()
    job.status = "completed"
    job.lease_expires_at = None
    job.finished_at = now
    job.error_message = None
    job.output_text = payload.output_text if payload is not None else None
    job.output_artifact_key = artifact_key
    job.output_artifact_url = payload.output_artifact_url if payload is not None else None
    job.output_artifact_content_type = payload.output_artifact_content_type if payload is not None else None
    job.output_artifact_size_bytes = payload.output_artifact_size_bytes if payload is not None else None
    job.output_artifact_etag = payload.output_artifact_etag if payload is not None else None
    brief = db.get(Brief, job.brief_id)
    legacy_content_generation_request, legacy_dna_generation_request, legacy_ticket_processing_request = _legacy_completion_requests(brief)
    if payload is not None and payload.output_text is not None:
        if job.kind == 'content_generation' or (job.kind == 'manual' and legacy_content_generation_request is not None):
            content_generation_request = legacy_content_generation_request or {}
            target_content_item_id = job.target_content_item_id or UUID(content_generation_request['content_item_id'])
            target_content_item = db.get(ContentItem, target_content_item_id)
            if target_content_item is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found for generated job')
            if target_content_item.organization_id != job.organization_id or target_content_item.brand_id != job.brand_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated content item does not belong to job scope')
            version_number = next_content_version_number(db, target_content_item.id)
            generation_type = GenerationType.INITIAL if version_number == 1 else GenerationType.REVISION
            content_version = create_content_version_record(
                db=db,
                content_item=target_content_item,
                organization_id=target_content_item.organization_id,
                version_number=version_number,
                body_markdown=payload.output_text,
                structured_json={
                    'source_job_id': str(job.id),
                    'source_brief_id': str(job.brief_id),
                    'content_generation_request': content_generation_request,
                    'worker_output_artifact_key': artifact_key,
                    'worker_output_artifact_url': payload.output_artifact_url,
                },
                change_summary='Generated from content item job completion',
                generation_type=generation_type,
                generated_from_task_id=job.id,
                created_by=None,
                is_current=True,
            )
            create_quality_check_record(
                db=db,
                content_item=target_content_item,
                organization_id=target_content_item.organization_id,
                content_version=content_version,
                current_user=None,
                ticket=None,
                generated_from_task_id=job.id,
                checked_at=now,
            )
        elif job.kind == 'dna_generation' or (job.kind == 'manual' and legacy_dna_generation_request is not None):
            generated_dna = json.loads(payload.output_text)
            if not isinstance(generated_dna, dict):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated DNA payload must be a JSON object')
            target_brand_id = job.target_brand_id or (UUID(legacy_dna_generation_request['brand_id']) if legacy_dna_generation_request and legacy_dna_generation_request.get('brand_id') else None)
            target_product_id = job.target_product_id or (UUID(legacy_dna_generation_request['product_id']) if legacy_dna_generation_request and legacy_dna_generation_request.get('product_id') else None)
            if target_brand_id is not None and target_product_id is not None:
                target_product = db.get(Product, target_product_id)
                if target_product is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found for generated DNA job')
                if target_product.organization_id != job.organization_id or target_product.brand_id != job.brand_id:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated product does not belong to job scope')
                target_product.dna_json = {
                    'kind': 'product_dna_generation',
                    'source_job_id': str(job.id),
                    'source_brief_id': str(job.brief_id),
                    'dna': generated_dna,
                }
            elif target_product_id is not None:
                target_product = db.get(Product, target_product_id)
                if target_product is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found for generated DNA job')
                if target_product.organization_id != job.organization_id or target_product.brand_id != job.brand_id:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated product does not belong to job scope')
                target_product.dna_json = {
                    'kind': 'product_dna_generation',
                    'source_job_id': str(job.id),
                    'source_brief_id': str(job.brief_id),
                    'dna': generated_dna,
                }
            elif target_brand_id is not None:
                target_brand = db.get(Brand, target_brand_id)
                if target_brand is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Brand not found for generated DNA job')
                if target_brand.organization_id != job.organization_id:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated brand does not belong to job scope')
                target_brand.dna_json = {
                    'kind': 'brand_dna_generation',
                    'source_job_id': str(job.id),
                    'source_brief_id': str(job.brief_id),
                    'dna': generated_dna,
                }
        elif job.kind == 'ticket_processing' or (job.kind == 'manual' and legacy_ticket_processing_request is not None):
            ticket_processing_request = legacy_ticket_processing_request or {}
            target_ticket_id = job.target_ticket_id or UUID(ticket_processing_request['ticket_id'])
            target_content_item_id = job.target_content_item_id or UUID(ticket_processing_request['content_item_id'])
            target_ticket = db.get(Ticket, target_ticket_id)
            if target_ticket is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Ticket not found for generated revision job')
            if target_ticket.organization_id != job.organization_id or target_ticket.brand_id != job.brand_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated ticket does not belong to job scope')
            target_content_item = db.get(ContentItem, target_content_item_id)
            if target_content_item is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found for generated ticket job')
            if target_content_item.organization_id != job.organization_id or target_content_item.brand_id != job.brand_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Generated content item does not belong to job scope')
            version_number = next_content_version_number(db, target_content_item.id)
            content_version = create_content_version_record(
                db=db,
                content_item=target_content_item,
                organization_id=target_content_item.organization_id,
                version_number=version_number,
                body_markdown=payload.output_text,
                structured_json={
                    'source_job_id': str(job.id),
                    'source_brief_id': str(job.brief_id),
                    'source_ticket_id': str(target_ticket.id),
                    'ticket_type': target_ticket.type,
                    'ticket_reason_codes': list(target_ticket.reason_codes or []),
                    'ticket_comment': target_ticket.comment,
                    'ticket_processing_request': ticket_processing_request,
                    'worker_output_artifact_key': artifact_key,
                    'worker_output_artifact_url': payload.output_artifact_url,
                },
                change_summary='Generated from ticket processing job completion',
                generation_type=GenerationType.REVISION,
                generated_from_task_id=job.id,
                created_by=None,
                is_current=True,
            )
            create_quality_check_record(
                db=db,
                content_item=target_content_item,
                organization_id=target_content_item.organization_id,
                content_version=content_version,
                current_user=None,
                ticket=target_ticket,
                generated_from_task_id=job.id,
                checked_at=now,
            )
            target_ticket.status = 'resolved'
            target_ticket.resolved_at = now
    trace = _ensure_execution_trace(job)
    _append_stage(trace, 'completed')
    _begin_stage(trace, 'completed', now)
    _close_active_stage(trace, now)
    trace['artifact_scope_status'] = 'validated' if artifact_key is not None else None
    trace['final_status'] = 'completed'
    trace['failure_reason'] = None
    trace['failure_stage'] = None
    trace['failure_code'] = None
    trace['validation_result'] = (
        _validation_result_snapshot(
            'validated',
            artifact_scope_status=trace['artifact_scope_status'],
            artifact_key=artifact_key,
        )
        if artifact_key is not None
        else None
    )
    _refresh_trace_derived_fields(trace)
    _append_event(
        trace,
        'completed',
        now,
        worker_id=worker_id,
        artifact_scope_status=trace['artifact_scope_status'],
        artifact=_artifact_trace_snapshot(payload),
        validation_result=trace.get('validation_result'),
        progress_context=trace.get('last_progress'),
        attempt_snapshot=trace.get('attempt_summary'),
        trace_summary=_trace_summary(trace),
        progress_digest=_progress_digest(trace),
        timeline_digest=_timeline_digest(trace),
        scope_recap=_scope_recap(trace),
        worker_recap=_worker_recap(trace),
        progress_window=_progress_window(trace),
        **_terminal_event_metrics(trace, now),
    )
    _write_execution_trace(job, trace)
    job.last_stage = 'completed'
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.post("/{job_id}/fail", response_model=JobRead)
def fail_job(
    job_id: UUID,
    payload: JobFailureRequest,
    worker_id: str = Depends(require_worker_context),
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, job_id)
    if job.status != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not running")
    _require_active_owner_lease(job, worker_id)
    now = _now()
    job.status = "failed"
    job.lease_expires_at = None
    job.finished_at = now
    job.error_message = payload.error_message
    trace = _ensure_execution_trace(job)
    failure_stage = _current_failure_stage(trace)
    failure_code = _classify_failure_code(payload.error_message)
    _append_stage(trace, 'failed')
    _begin_stage(trace, 'failed', now)
    _close_active_stage(trace, now)
    if failure_code == 'artifact_scope_rejection':
        trace['artifact_scope_status'] = 'rejected'
    trace['final_status'] = 'failed'
    trace['failure_reason'] = payload.error_message
    trace['failure_stage'] = failure_stage
    trace['failure_code'] = failure_code
    trace['validation_result'] = (
        _validation_result_snapshot(
            'rejected',
            artifact_scope_status=trace['artifact_scope_status'],
            reason=payload.error_message,
            failure_code=failure_code,
        )
        if failure_code == 'artifact_scope_rejection'
        else None
    )
    _refresh_trace_derived_fields(trace)
    _append_event(
        trace,
        'failed',
        now,
        worker_id=worker_id,
        failure_reason=payload.error_message,
        failure_stage=failure_stage,
        failure_code=failure_code,
        progress_context=trace.get('last_progress'),
        attempt_snapshot=trace.get('attempt_summary'),
        trace_summary=_trace_summary(trace),
        progress_digest=_progress_digest(trace),
        timeline_digest=_timeline_digest(trace),
        scope_recap=_scope_recap(trace),
        worker_recap=_worker_recap(trace),
        progress_window=_progress_window(trace),
        failure_digest=_failure_digest(trace),
        artifact_scope_status=trace['artifact_scope_status'],
        validation_result=trace.get('validation_result'),
        **_terminal_event_metrics(trace, now),
    )
    _write_execution_trace(job, trace)
    job.last_stage = 'failed'
    db.commit()
    db.refresh(job)
    return _job_read(job)
