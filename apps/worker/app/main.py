import re
import time

import httpx

from app.api_client import WorkerApiClient
from app.config import get_settings
from app.llm_client import OpenRouterRoleExecutor
from app.storage import expected_artifact_key, persist_result_artifact


def _process_stages(settings) -> list[str]:
    raw = getattr(settings, 'worker_process_stages', 'fetch-payload,render-output') or 'fetch-payload,render-output'
    return [stage.strip() for stage in raw.split(',') if stage.strip()]


def _slugify_title(title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return slug or 'job-output'


def _resolved_worker_stages(settings, job: dict) -> list[dict[str, object]]:
    internal_role_plan = job.get('internal_role_plan') or []
    execution_profile = job.get('execution_profile')
    role_stages: list[dict[str, object]] = []
    if isinstance(internal_role_plan, list) and internal_role_plan:
        role_count = len(internal_role_plan)
        for index, item in enumerate(internal_role_plan, start=1):
            if not isinstance(item, dict):
                continue
            role_id = item.get('role_id')
            label = item.get('label')
            if not isinstance(role_id, str) or not role_id:
                continue
            if not isinstance(label, str) or not label:
                label = role_id.replace('-', ' ').title()
            progress_percent = round(index * 100 / role_count)
            role_stages.append({
                'stage_name': f'role:{role_id}',
                'stage_label': label,
                'progress_percent': progress_percent,
                'progress_message': f'Executing internal role {label}',
                'transition_tag': f'internal-role:{role_id}',
                'worker_metadata': {
                    'role_id': role_id,
                    'role_label': label,
                    'execution_profile': execution_profile,
                    'role_index': index,
                    'role_count': role_count,
                },
            })
    if role_stages:
        return role_stages
    return [{'stage_name': stage} for stage in _process_stages(settings)]


def _role_output_slug(job: dict) -> str:
    return f"internal-role-output-{_slugify_title(job['title'])}"


def _build_role_executor(settings):
    return OpenRouterRoleExecutor(settings)


def _compile_role_specific_output(job: dict, stages: list[dict[str, object]], role_outputs: list[dict[str, object]]) -> str:
    execution_profile = job.get('execution_profile') or 'unknown'
    compiled_lines: list[str] = []
    compiled_lines.append('# Internal role execution output')
    compiled_lines.append(f"**Job:** {job['title']}")
    compiled_lines.append(f"**Execution profile:** `{execution_profile}`")
    compiled_lines.append('')
    role_names: list[str] = []
    for index, role_output in enumerate(role_outputs, start=1):
        role_id = str(role_output.get('role_id') or '').strip()
        label = str(role_output.get('label') or role_id).strip() or role_id
        purpose = str(role_output.get('purpose') or 'No purpose provided').strip()
        role_text = str(role_output.get('output') or '').strip()
        role_names.append(label)
        compiled_lines.append(f"## {index}. {label} (`{role_id}`)")
        compiled_lines.append(f"**Purpose:** {purpose}")
        compiled_lines.append('Role output:')
        compiled_lines.append(role_text or '_No output returned._')
        compiled_lines.append('')
    compiled_lines.append('## Final compiled result')
    if role_names:
        compiled_lines.append(' -> '.join(role_names))
    else:
        compiled_lines.append('No internal roles available.')
    compiled_lines.append('')
    compiled_lines.append(f"Compiled by worker stages: {', '.join(str(stage['stage_name']) for stage in stages)}")
    return '\n'.join(compiled_lines)


def _artifact_reference(settings, job: dict, result: str, artifact_slug: str | None = None) -> dict[str, str]:
    if hasattr(settings, 's3_bucket'):
        try:
            return persist_result_artifact(settings, job, result)
        except TypeError:
            return persist_result_artifact(settings, result)
        except AttributeError:
            pass
    key_source = artifact_slug or result
    key = expected_artifact_key(job) or f'jobs/{key_source}.txt'
    return {
        'key': key,
        'url': f's3://cf-artifacts/{key}',
        'content_type': 'text/plain',
    }


def _assert_artifact_scope(job: dict, artifact: dict | None) -> None:
    if artifact is None:
        return
    expected_key = expected_artifact_key(job)
    if expected_key is None:
        return
    actual_key = artifact.get('key')
    if actual_key != expected_key:
        raise ValueError('artifact key escaped job scope')


def process_job(settings, client: WorkerApiClient, job: dict, skip_first_renew: bool = False) -> dict:
    stages = _resolved_worker_stages(settings, job)
    role_aware = bool(job.get('internal_role_plan'))
    role_executor = _build_role_executor(settings) if role_aware else None
    role_outputs: list[dict[str, object]] = []
    role_plan = job.get('internal_role_plan') or []
    for index, stage in enumerate(stages):
        stage_name = str(stage['stage_name'])
        if not (skip_first_renew and index == 0):
            heartbeat_kwargs = {'stage_name': stage_name}
            if isinstance(stage.get('stage_label'), str):
                heartbeat_kwargs['stage_label'] = stage['stage_label']
            if isinstance(stage.get('progress_percent'), int):
                heartbeat_kwargs['progress_percent'] = stage['progress_percent']
            if isinstance(stage.get('progress_message'), str):
                heartbeat_kwargs['progress_message'] = stage['progress_message']
            if isinstance(stage.get('transition_tag'), str):
                heartbeat_kwargs['transition_tag'] = stage['transition_tag']
            if isinstance(stage.get('worker_metadata'), dict):
                heartbeat_kwargs['worker_metadata'] = stage['worker_metadata']
            client.heartbeat_job(job['id'], **heartbeat_kwargs)
        print(f"cf-worker stage {stage_name} for job {job['id']}", flush=True)
        if role_aware and index < len(role_plan) and isinstance(role_plan[index], dict):
            role = role_plan[index]
            if role_executor is None:
                raise RuntimeError('role executor is required for role-aware jobs')
            role_outputs.append({
                'role_id': str(role.get('role_id') or '').strip(),
                'label': str(role.get('label') or role.get('role_id') or '').strip(),
                'purpose': str(role.get('purpose') or 'No purpose provided').strip(),
                'output': role_executor.execute_role(
                    job=job,
                    role=role,
                    stage=stage,
                    previous_outputs=role_outputs,
                ),
            })
    if role_aware:
        result = _compile_role_specific_output(job, stages, role_outputs)
    else:
        result = f"stub-output-for-{_slugify_title(job['title'])}"
    artifact = _artifact_reference(settings, job, result, _role_output_slug(job) if role_aware else None)
    _assert_artifact_scope(job, artifact)
    return {
        'job_id': job['id'],
        'title': job['title'],
        'stages': [str(stage['stage_name']) for stage in stages],
        'result': result,
        'artifact': artifact,
        'role_outputs': role_outputs if role_aware else [],
    }


def run_loop_once(settings, client: WorkerApiClient, process_job_fn=process_job) -> str:
    try:
        job = client.claim_next_job()
    except httpx.HTTPStatusError:
        raise
    if job is None:
        print('cf-worker idle: no queued jobs available', flush=True)
        return 'idle'

    job_id = job['id']
    print(f"cf-worker claimed job {job_id}", flush=True)
    initial_stages = _resolved_worker_stages(settings, job)
    initial_stage = initial_stages[0] if initial_stages and isinstance(initial_stages[0], dict) else None
    if initial_stage is not None and isinstance(initial_stage.get('stage_label'), str):
        heartbeat_kwargs = {'stage_name': str(initial_stage['stage_name'])}
        if isinstance(initial_stage.get('stage_label'), str):
            heartbeat_kwargs['stage_label'] = initial_stage['stage_label']
        if isinstance(initial_stage.get('progress_percent'), int):
            heartbeat_kwargs['progress_percent'] = initial_stage['progress_percent']
        if isinstance(initial_stage.get('progress_message'), str):
            heartbeat_kwargs['progress_message'] = initial_stage['progress_message']
        if isinstance(initial_stage.get('transition_tag'), str):
            heartbeat_kwargs['transition_tag'] = initial_stage['transition_tag']
        if isinstance(initial_stage.get('worker_metadata'), dict):
            heartbeat_kwargs['worker_metadata'] = initial_stage['worker_metadata']
        client.heartbeat_job(job_id, **heartbeat_kwargs)
    else:
        client.heartbeat_job(job_id)
    print(f"cf-worker renewed lease for job {job_id}", flush=True)
    try:
        if process_job_fn is process_job:
            process_result = process_job_fn(settings, client, job, skip_first_renew=True)
        else:
            process_result = process_job_fn(settings, client, job)
    except Exception as exc:
        client.fail_job(job_id, f'processing error: {exc}')
        print(f"cf-worker failed job {job_id}: {exc}", flush=True)
        return 'failed'

    output_text = process_result.get('result') if isinstance(process_result, dict) else None
    artifact = process_result.get('artifact') if isinstance(process_result, dict) else None
    client.complete_job(job_id, output_text=output_text, artifact=artifact)
    print(f"cf-worker completed job {job_id}", flush=True)
    return 'completed'


def run_once() -> None:
    settings = get_settings()
    if not settings.worker_once_action:
        raise RuntimeError('worker_once_action is required for one-shot mode')
    client = WorkerApiClient(settings)
    action = settings.worker_once_action.lower()
    if action == 'claim-next':
        result = client.claim_next_job()
    elif action == 'claim':
        if not settings.worker_once_job_id:
            raise RuntimeError('worker_once_job_id is required for claim mode')
        result = client.claim_job(settings.worker_once_job_id)
    elif action == 'heartbeat':
        if not settings.worker_once_job_id:
            raise RuntimeError('worker_once_job_id is required for heartbeat mode')
        result = client.heartbeat_job(settings.worker_once_job_id)
    elif action == 'complete':
        if not settings.worker_once_job_id:
            raise RuntimeError('worker_once_job_id is required for complete mode')
        result = client.complete_job(settings.worker_once_job_id)
    elif action == 'fail':
        if not settings.worker_once_job_id:
            raise RuntimeError('worker_once_job_id is required for fail mode')
        result = client.fail_job(settings.worker_once_job_id, settings.worker_once_error_message or 'worker failure')
    else:
        raise RuntimeError(f'Unsupported worker_once_action: {settings.worker_once_action}')
    print(f'cf-worker one-shot {action}: {result}', flush=True)


def main():
    settings = get_settings()
    if settings.worker_once_action:
        run_once()
        return
    client = WorkerApiClient(settings)
    print('cf-worker started polling loop', flush=True)
    while True:
        run_loop_once(settings, client)
        time.sleep(settings.worker_poll_seconds)


if __name__ == '__main__':
    main()
