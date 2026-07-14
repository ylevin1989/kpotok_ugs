'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';
import { loadScopeSelection, loadSession } from '../../lib/auth';
import { getOrganizations, getUsageRecords, listSubscriptions, upsertSubscription } from '../../lib/api';
import type { OrganizationRead, SubscriptionCreateInput, SubscriptionRead, UsageRecordRead } from '../../lib/types';

const DEFAULT_FORM: SubscriptionCreateInput = {
  organization_id: '',
  plan_name: 'starter',
  monthly_content_plan_limit: 25,
  monthly_export_limit: 5,
  is_active: true,
  current_period_start: new Date().toISOString().slice(0, 10),
  current_period_end: new Date().toISOString().slice(0, 10),
};

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU');
}

export default function SubscriptionsPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionRead | null>(null);
  const [usage, setUsage] = useState<UsageRecordRead[]>([]);
  const [form, setForm] = useState<SubscriptionCreateInput>(DEFAULT_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const session = loadSession();
    if (!session) {
      router.replace('/login');
      return;
    }
    const scope = loadScopeSelection();
    if (!scope?.organizationId) {
      setError('Сначала выбери организацию и бренд на панели');
      setLoading(false);
      return;
    }
    const token = session.accessToken;
    const orgId = scope.organizationId;
    setAccessToken(token);
    setOrganizationId(orgId);
    setForm((current) => ({ ...current, organization_id: orgId }));

    let cancelled = false;
    async function bootstrap() {
      try {
        const [orgResponse, subResponse, usageResponse] = await Promise.all([
          getOrganizations(token),
          listSubscriptions(token, orgId),
          getUsageRecords(token, orgId),
        ]);
        if (cancelled) return;
        setOrganizations(orgResponse.items);
        const current = subResponse.items[0] ?? null;
        setSubscription(current);
        setUsage(usageResponse.items);
        if (current) {
          setForm({
            organization_id: current.organization_id,
            plan_name: current.plan_name,
            monthly_content_plan_limit: current.monthly_content_plan_limit,
            monthly_export_limit: current.monthly_export_limit,
            is_active: current.is_active,
            current_period_start: current.current_period_start,
            current_period_end: current.current_period_end,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить данные подписки');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !organizationId) {
      setError('Нет активной организации');
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await upsertSubscription(accessToken, { ...form, organization_id: organizationId });
      setSubscription(saved);
      setNotice(`Подписка обновлена: ${saved.plan_name}`);
      const usageResponse = await getUsageRecords(accessToken, organizationId);
      setUsage(usageResponse.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить подписку');
    } finally {
      setSaving(false);
    }
  }

  const currentOrganization = organizationId ? organizations.find((item) => item.id === organizationId) ?? null : null;

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Подписки</span>
          <h1>Планы, лимиты и использование</h1>
          <p className="muted">Управление строкой подписки, лимитами и записью событий использования.</p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Панель</Link>
          <Link className="secondary-button" href="/content-plans">Контент-планы</Link>
        </div>
      </section>

      {error ? (
        <section className="card stack-sm error-card">
          <h2>Ошибка</h2>
          <p>{error}</p>
        </section>
      ) : null}

      {notice ? (
        <section className="card stack-sm">
          <h2>Статус</h2>
          <p className="muted">{notice}</p>
        </section>
      ) : null}

      <section className="grid two-up">
        <article className="card stack-sm">
          <h2>Текущая подписка</h2>
          <dl className="keyvals">
            <div><dt>Организация</dt><dd>{currentOrganization ? currentOrganization.name : organizationId ?? '—'}</dd></div>
            <div><dt>Тариф</dt><dd>{subscription?.plan_name ?? '—'}</dd></div>
            <div><dt>Лимит контента</dt><dd>{subscription?.monthly_content_plan_limit ?? '—'}</dd></div>
            <div><dt>Лимит экспорта</dt><dd>{subscription?.monthly_export_limit ?? '—'}</dd></div>
            <div><dt>Активен</dt><dd>{subscription ? (subscription.is_active ? 'да' : 'нет') : '—'}</dd></div>
            <div><dt>Период</dt><dd>{subscription ? `${subscription.current_period_start} → ${subscription.current_period_end}` : '—'}</dd></div>
          </dl>
        </article>

        <article className="card stack-sm">
          <h2>Использование</h2>
          <div className="stack-sm">
            {usage.map((item) => (
              <div className="brief-card stack-xs" key={item.id}>
                <div className="brief-meta">
                  <strong>{item.metric}</strong>
                  <span className="pill subtle-pill">{item.quantity}</span>
                </div>
                <p className="brief-content">{item.window_start} → {item.window_end}</p>
                <span className="muted">Записано {formatDateTime(item.created_at)}</span>
              </div>
            ))}
            {usage.length === 0 ? <p className="muted">События использования не найдены.</p> : null}
          </div>
        </article>
      </section>

      <section className="card stack-md">
        <div className="section-header">
          <div>
            <h2>Редактировать подписку</h2>
            <p className="muted">Меняет лимиты и активность текущей организации.</p>
          </div>
        </div>

        <form className="stack-md" onSubmit={handleSubmit}>
          <label className="label-stack"><span>Название тарифа</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, plan_name: event.target.value }))} value={form.plan_name} /></label>
          <div className="grid two-up">
            <label className="label-stack"><span>Месячный лимит контент-планов</span><input className="input" min={0} onChange={(event) => setForm((current) => ({ ...current, monthly_content_plan_limit: Number(event.target.value) }))} type="number" value={form.monthly_content_plan_limit} /></label>
            <label className="label-stack"><span>Месячный лимит экспорта</span><input className="input" min={0} onChange={(event) => setForm((current) => ({ ...current, monthly_export_limit: Number(event.target.value) }))} type="number" value={form.monthly_export_limit} /></label>
          </div>
          <div className="grid two-up">
            <label className="label-stack"><span>Начало текущего периода</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, current_period_start: event.target.value }))} type="date" value={form.current_period_start} /></label>
            <label className="label-stack"><span>Конец текущего периода</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, current_period_end: event.target.value }))} type="date" value={form.current_period_end} /></label>
          </div>
          <label className="label-stack">
            <span>Активен</span>
            <select className="input" onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.value === 'true' }))} value={String(form.is_active)}>
              <option value="true">да</option>
              <option value="false">нет</option>
            </select>
          </label>
          <button className="primary-button" disabled={saving} type="submit">
            {saving ? 'Сохраняем…' : 'Сохранить подписку'}
          </button>
        </form>
      </section>
    </main>
  );
}
