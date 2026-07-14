'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { loadScopeSelection, loadSession } from '../../lib/auth';
import { createBrand, generateBrandDna, getBrands, getOrganizations, updateBrand } from '../../lib/api';
import type { BrandCreateInput, BrandRead, OrganizationRead } from '../../lib/types';

type BrandFormState = {
  name: string;
  slug: string;
  status: string;
  positioning: string;
  tone_of_voice: string;
  mission: string;
  values: string;
  forbidden_claims: string;
  allowed_claims: string;
  competitors: string;
  good_examples: string;
  bad_examples: string;
};

const EMPTY_FORM: BrandFormState = {
  name: '',
  slug: '',
  status: 'active',
  positioning: '',
  tone_of_voice: '',
  mission: '',
  values: '',
  forbidden_claims: '',
  allowed_claims: '',
  competitors: '',
  good_examples: '',
  bad_examples: '',
};

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU');
}

function joinList(items: string[] | null | undefined): string {
  return items?.join('\n') ?? '';
}

function getDnaRecord(dnaJson: Record<string, unknown> | null): Record<string, unknown> | null {
  if (!dnaJson || typeof dnaJson !== 'object') {
    return null;
  }

  const dna = dnaJson.dna;
  if (dna && typeof dna === 'object' && !Array.isArray(dna)) {
    return dna as Record<string, unknown>;
  }

  return dnaJson;
}

function findTextDeep(record: unknown, keys: string[], seen = new Set<unknown>()): string | null {
  if (!record || typeof record !== 'object' || seen.has(record)) {
    return null;
  }
  seen.add(record);

  if (Array.isArray(record)) {
    for (const item of record) {
      const found = findTextDeep(item, keys, seen);
      if (found) return found;
    }
    return null;
  }

  for (const [key, value] of Object.entries(record as Record<string, unknown>)) {
    if (keys.includes(key) && typeof value === 'string' && value.trim()) {
      return value.trim();
    }
    const found = findTextDeep(value, keys, seen);
    if (found) return found;
  }

  return null;
}

function findAnyTextDeep(record: unknown, seen = new Set<unknown>()): string | null {
  if (typeof record === 'string') {
    const trimmed = record.trim();
    return trimmed || null;
  }
  if (!record || typeof record !== 'object' || seen.has(record)) {
    return null;
  }
  seen.add(record);

  if (Array.isArray(record)) {
    for (const item of record) {
      const found = findAnyTextDeep(item, seen);
      if (found) return found;
    }
    return null;
  }

  for (const value of Object.values(record as Record<string, unknown>)) {
    const found = findAnyTextDeep(value, seen);
    if (found) return found;
  }

  return null;
}

function findListDeep(record: unknown, keys: string[], seen = new Set<unknown>()): string[] | null {
  if (!record || typeof record !== 'object' || seen.has(record)) {
    return null;
  }
  seen.add(record);

  if (Array.isArray(record)) {
    const items = record.flatMap((item) => (typeof item === 'string' ? [item.trim()] : [])).filter(Boolean);
    if (items.length) return items;
    for (const item of record) {
      const found = findListDeep(item, keys, seen);
      if (found) return found;
    }
    return null;
  }

  for (const [key, value] of Object.entries(record as Record<string, unknown>)) {
    if (keys.includes(key)) {
      if (Array.isArray(value)) {
        const items = value.map((item) => (typeof item === 'string' ? item.trim() : '')).filter(Boolean);
        if (items.length) return items;
      } else if (typeof value === 'string') {
        const items = value
          .split('\n')
          .flatMap((line) => line.split(','))
          .map((item) => item.trim())
          .filter(Boolean);
        if (items.length) return items;
      }
    }
    const found = findListDeep(value, keys, seen);
    if (found) return found;
  }

  return null;
}

function readText(record: Record<string, unknown> | null, keys: string[]): string | null {
  return findTextDeep(record, keys);
}

function readList(record: Record<string, unknown> | null, keys: string[]): string[] | null {
  return findListDeep(record, keys);
}

function composeBrandSummary(record: Record<string, unknown> | null): string | null {
  const parts = [
    readText(record, ['positioning', 'position', 'brand_positioning', 'value_proposition']),
    readText(record, ['mission', 'brand_mission', 'purpose']),
    readList(record, ['values', 'brand_values', 'traits', 'tone_of_voice'])?.slice(0, 3).join(', '),
  ].filter((item): item is string => Boolean(item && item.trim()));

  if (parts.length) {
    return parts.join(' · ');
  }

  const anyText = findAnyTextDeep(record);
  if (!anyText) return null;
  return anyText.length > 180 ? `${anyText.slice(0, 177)}…` : anyText;
}

function prettyList({ items }: { items: string[] | null | undefined }) {
  if (!items || items.length === 0) {
    return <p className="muted">—</p>;
  }

  return (
    <ul className="stack-xs">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function splitList(value: string): string[] | null {
  const items = value
    .split('\n')
    .flatMap((line) => line.split(','))
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : null;
}

function brandToFormState(brand: BrandRead): BrandFormState {
  return {
    name: brand.name,
    slug: brand.slug,
    status: brand.status,
    positioning: brand.positioning ?? '',
    tone_of_voice: joinList(brand.tone_of_voice),
    mission: brand.mission ?? '',
    values: joinList(brand.values),
    forbidden_claims: joinList(brand.forbidden_claims),
    allowed_claims: joinList(brand.allowed_claims),
    competitors: joinList(brand.competitors),
    good_examples: joinList(brand.good_examples),
    bad_examples: joinList(brand.bad_examples),
  };
}

function buildBrandPayload(form: BrandFormState, organizationId: string): BrandCreateInput {
  return {
    organization_id: organizationId,
    name: form.name.trim(),
    slug: form.slug.trim(),
    status: form.status || undefined,
    positioning: form.positioning.trim() || null,
    tone_of_voice: splitList(form.tone_of_voice),
    mission: form.mission.trim() || null,
    values: splitList(form.values),
    forbidden_claims: splitList(form.forbidden_claims),
    allowed_claims: splitList(form.allowed_claims),
    competitors: splitList(form.competitors),
    good_examples: splitList(form.good_examples),
    bad_examples: splitList(form.bad_examples),
  };
}

export default function BrandsPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<BrandFormState>(EMPTY_FORM);
  const [editForm, setEditForm] = useState<BrandFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
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
      setError('Сначала выбери organization на dashboard');
      setIsLoading(false);
      return;
    }

    const token = session.accessToken;
    const orgId = scope.organizationId;
    setAccessToken(token);
    setOrganizationId(orgId);

    let cancelled = false;

    async function bootstrap() {
      try {
        const [orgResponse, brandResponse] = await Promise.all([getOrganizations(token), getBrands(token, orgId)]);
        if (cancelled) {
          return;
        }
        setOrganizations(orgResponse.items);
        setBrands(brandResponse.items);
        const firstBrand = brandResponse.items[0] ?? null;
        setSelectedBrandId(firstBrand?.id ?? null);
        setEditForm(firstBrand ? brandToFormState(firstBrand) : EMPTY_FORM);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить бренды');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    const selectedBrand = selectedBrandId ? brands.find((brand) => brand.id === selectedBrandId) ?? null : null;
    setEditForm(selectedBrand ? brandToFormState(selectedBrand) : EMPTY_FORM);
  }, [brands, selectedBrandId]);

  const selectedBrand = useMemo(
    () => brands.find((brand) => brand.id === selectedBrandId) ?? null,
    [brands, selectedBrandId],
  );
  const dnaRecord = useMemo(() => getDnaRecord(selectedBrand?.dna_json ?? null), [selectedBrand]);

  const currentOrganization = organizationId ? organizations.find((item) => item.id === organizationId) ?? null : null;
  const hasOnlyOneBrand = brands.length === 1;

  async function handleGenerateDna(brandId: string) {
    if (!accessToken) {
      return;
    }
    setIsGenerating(brandId);
    setError(null);
    setNotice(null);
    try {
      await generateBrandDna(accessToken, brandId);
      setNotice('Job на генерацию Brand DNA создан');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить Brand DNA');
    } finally {
      setIsGenerating(null);
    }
  }

  async function handleCreateBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !organizationId) {
      return;
    }
    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createBrand(accessToken, buildBrandPayload(createForm, organizationId));
      setBrands((current) => [...current, created]);
      setSelectedBrandId(created.id);
      setCreateForm(EMPTY_FORM);
      setNotice('Бренд создан');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать бренд');
    } finally {
      setIsCreating(false);
    }
  }

  async function handleUpdateBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !selectedBrandId || !organizationId) {
      return;
    }
    setIsUpdating(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateBrand(accessToken, selectedBrandId, buildBrandPayload(editForm, organizationId));
      setBrands((current) => current.map((brand) => (brand.id === updated.id ? updated : brand)));
      setSelectedBrandId(updated.id);
      setNotice('Бренд обновлён');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить бренд');
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Бренды</span>
          <h1>Брендовый кабинет</h1>
          <p className="muted">
            Здесь живёт первый брендовый slice: список брендов в текущем organization scope, создание/редактирование
            Brand DNA fields и запуск Brand DNA.
          </p>
        </div>
        <Link className="secondary-button" href="/dashboard">
          Назад в панель
        </Link>
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
          <h2>Область</h2>
          <dl className="keyvals">
            <div>
              <dt>Организация</dt>
              <dd>{currentOrganization ? currentOrganization.name : organizationId ?? '—'}</dd>
            </div>
            <div>
              <dt>Загружено брендов</dt>
              <dd>{brands.length}</dd>
            </div>
          </dl>
        </article>

        <article className="card stack-sm">
          <h2>Что уже доступно</h2>
          <ul className="checklist">
            <li>список брендов читается из live API</li>
            <li>задачу ДНК бренда можно запускать прямо отсюда</li>
            <li>создание и обновление бренда работают с полями ДНК бренда</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Список брендов</h2>
              <p className="muted">
                Выбери бренд, чтобы редактировать его справа. Сейчас в области {brands.length} бренд{brands.length === 1 ? '' : 'а'}.
              </p>
            </div>
          </div>

          <div className="table-like">
            {brands.map((brand) => (
              <div className="row" key={brand.id}>
                <div className="stack-sm" style={{ flex: 1 }}>
                  <div className="row">
                    <div>
                      <div className="row-value">{brand.name}</div>
                      <div className="row-label">{brand.slug}</div>
                    </div>
                    <span className="pill">{brand.status}</span>
                    <span className="pill">{brand.dna_json ? 'ДНК готова' : 'ДНК пустая'}</span>
                    {selectedBrandId === brand.id ? <span className="pill">Выбран</span> : null}
                  </div>
                  <p className="row-label">Создан {formatDateTime(brand.created_at)}</p>
                </div>
                <div className="stack-sm">
                  <button className="secondary-button" onClick={() => setSelectedBrandId(brand.id)} type="button">
                    Выбрать
                  </button>
                  <button className="secondary-button" disabled={isGenerating === brand.id} onClick={() => handleGenerateDna(brand.id)} type="button">
                    {isGenerating === brand.id ? 'Генерируем…' : 'Обновить ДНК бренда'}
                  </button>
                </div>
              </div>
            ))}
            {!isLoading && brands.length === 0 ? <p className="muted">Пока нет брендов в выбранной области организации.</p> : null}
            {!isLoading && hasOnlyOneBrand ? <p className="muted">Сейчас в области только один бренд — это нормальный сценарий для первого запуска.</p> : null}
          </div>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Карточка бренда</h2>
              <p className="muted">Текущие Brand DNA поля и JSON payload.</p>
            </div>
          </div>

          {selectedBrand ? (
            <div className="stack-sm">
              <dl className="keyvals">
                <div><dt>Название</dt><dd>{selectedBrand.name}</dd></div>
                <div><dt>Слаг</dt><dd>{selectedBrand.slug}</dd></div>
                <div><dt>Позиционирование</dt><dd>{selectedBrand.positioning ?? readText(dnaRecord, ['positioning', 'position', 'brand_positioning', 'позиционирование']) ?? '—'}</dd></div>
                <div><dt>Миссия</dt><dd>{selectedBrand.mission ?? readText(dnaRecord, ['mission', 'миссия']) ?? '—'}</dd></div>
                <div><dt>Обновлено</dt><dd>{formatDateTime(selectedBrand.updated_at)}</dd></div>
              </dl>

              <div className="card stack-sm subtle-card">
                <div className="row-label">Характер бренда</div>
                {prettyList({ items: selectedBrand.tone_of_voice ?? readList(dnaRecord, ['tone_of_voice', 'toneOfVoice', 'voice', 'character', 'characteristics', 'характер']) })}

                <div className="row-label">Ценности</div>
                {prettyList({ items: selectedBrand.values ?? readList(dnaRecord, ['values', 'brand_values', 'ценности']) })}

                <div className="row-label">Запрещённые формулировки</div>
                {prettyList({ items: selectedBrand.forbidden_claims ?? readList(dnaRecord, ['forbidden_claims', 'forbiddenClaims', 'claims_forbidden', 'запрещённые_формулировки']) })}

                <div className="row-label">Разрешённые формулировки</div>
                {prettyList({ items: selectedBrand.allowed_claims ?? readList(dnaRecord, ['allowed_claims', 'allowedClaims', 'claims_allowed', 'разрешённые_формулировки']) })}

                <div className="row-label">Конкуренты</div>
                {prettyList({ items: selectedBrand.competitors ?? readList(dnaRecord, ['competitors', 'competition', 'конкуренты']) })}

                <div className="row-label">Хорошие примеры</div>
                {prettyList({ items: selectedBrand.good_examples ?? readList(dnaRecord, ['good_examples', 'goodExamples', 'examples_good', 'хорошие_примеры']) })}

                <div className="row-label">Плохие примеры</div>
                {prettyList({ items: selectedBrand.bad_examples ?? readList(dnaRecord, ['bad_examples', 'badExamples', 'examples_bad', 'плохие_примеры']) })}
              </div>

              <div className="card stack-sm subtle-card">
                <div className="row-label">Ключевой вывод</div>
                <p>{composeBrandSummary(dnaRecord) ?? 'Данные бренда пока не заполнены'}</p>

                <details>
                  <summary>Показать технические данные</summary>
                  <dl className="keyvals">
                    <div><dt>Тип</dt><dd>{typeof dnaRecord?.kind === 'string' ? dnaRecord.kind : '—'}</dd></div>
                    <div><dt>Job ID</dt><dd>{typeof dnaRecord?.source_job_id === 'string' ? dnaRecord.source_job_id : '—'}</dd></div>
                    <div><dt>Brief ID</dt><dd>{typeof dnaRecord?.source_brief_id === 'string' ? dnaRecord.source_brief_id : '—'}</dd></div>
                  </dl>
                  <pre className="code-block">{selectedBrand.dna_json ? JSON.stringify(selectedBrand.dna_json, null, 2) : 'Brand DNA ещё не сгенерирован'}</pre>
                </details>
              </div>
            </div>
          ) : (
            <p className="muted">Выбери бренд слева, чтобы увидеть детали.</p>
          )}
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Создать бренд</h2>
              <p className="muted">Сразу задаём нужные Brand DNA поля.</p>
            </div>
          </div>

          <form className="stack-sm" onSubmit={handleCreateBrand}>
            <label className="stack-xs">
              <span>Название</span>
              <input className="input" required value={createForm.name} onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Слаг</span>
              <input className="input" required value={createForm.slug} onChange={(event) => setCreateForm((current) => ({ ...current, slug: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Статус</span>
              <select className="input" value={createForm.status} onChange={(event) => setCreateForm((current) => ({ ...current, status: event.target.value }))}>
                <option value="active">active</option>
                <option value="paused">paused</option>
                <option value="archived">archived</option>
              </select>
            </label>
            <label className="stack-xs">
              <span>Позиционирование</span>
              <textarea className="input" rows={2} value={createForm.positioning} onChange={(event) => setCreateForm((current) => ({ ...current, positioning: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Тон голоса</span>
              <textarea className="input" rows={3} value={createForm.tone_of_voice} onChange={(event) => setCreateForm((current) => ({ ...current, tone_of_voice: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Миссия</span>
              <textarea className="input" rows={2} value={createForm.mission} onChange={(event) => setCreateForm((current) => ({ ...current, mission: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Values</span>
              <textarea className="input" rows={3} value={createForm.values} onChange={(event) => setCreateForm((current) => ({ ...current, values: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Forbidden claims</span>
              <textarea className="input" rows={3} value={createForm.forbidden_claims} onChange={(event) => setCreateForm((current) => ({ ...current, forbidden_claims: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Allowed claims</span>
              <textarea className="input" rows={3} value={createForm.allowed_claims} onChange={(event) => setCreateForm((current) => ({ ...current, allowed_claims: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Competitors</span>
              <textarea className="input" rows={3} value={createForm.competitors} onChange={(event) => setCreateForm((current) => ({ ...current, competitors: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Good examples</span>
              <textarea className="input" rows={3} value={createForm.good_examples} onChange={(event) => setCreateForm((current) => ({ ...current, good_examples: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Bad examples</span>
              <textarea className="input" rows={3} value={createForm.bad_examples} onChange={(event) => setCreateForm((current) => ({ ...current, bad_examples: event.target.value }))} />
            </label>
            <button className="primary-button" disabled={isCreating} type="submit">
              {isCreating ? 'Создаём…' : 'Создать бренд'}
            </button>
          </form>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Редактировать бренд</h2>
              <p className="muted">Обновление выбранного brand record.</p>
            </div>
          </div>

          <form className="stack-sm" onSubmit={handleUpdateBrand}>
            <label className="stack-xs">
              <span>Brand</span>
              <select className="input" value={selectedBrandId ?? ''} onChange={(event) => setSelectedBrandId(event.target.value || null)}>
                <option value="">—</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>{brand.name}</option>
                ))}
              </select>
            </label>
            <label className="stack-xs">
              <span>Название</span>
              <input className="input" required value={editForm.name} onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Слаг</span>
              <input className="input" required value={editForm.slug} onChange={(event) => setEditForm((current) => ({ ...current, slug: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Статус</span>
              <select className="input" value={editForm.status} onChange={(event) => setEditForm((current) => ({ ...current, status: event.target.value }))}>
                <option value="active">active</option>
                <option value="paused">paused</option>
                <option value="archived">archived</option>
              </select>
            </label>
            <label className="stack-xs">
              <span>Позиционирование</span>
              <textarea className="input" rows={2} value={editForm.positioning} onChange={(event) => setEditForm((current) => ({ ...current, positioning: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Тон голоса</span>
              <textarea className="input" rows={3} value={editForm.tone_of_voice} onChange={(event) => setEditForm((current) => ({ ...current, tone_of_voice: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Миссия</span>
              <textarea className="input" rows={2} value={editForm.mission} onChange={(event) => setEditForm((current) => ({ ...current, mission: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Values</span>
              <textarea className="input" rows={3} value={editForm.values} onChange={(event) => setEditForm((current) => ({ ...current, values: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Forbidden claims</span>
              <textarea className="input" rows={3} value={editForm.forbidden_claims} onChange={(event) => setEditForm((current) => ({ ...current, forbidden_claims: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Allowed claims</span>
              <textarea className="input" rows={3} value={editForm.allowed_claims} onChange={(event) => setEditForm((current) => ({ ...current, allowed_claims: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Competitors</span>
              <textarea className="input" rows={3} value={editForm.competitors} onChange={(event) => setEditForm((current) => ({ ...current, competitors: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Good examples</span>
              <textarea className="input" rows={3} value={editForm.good_examples} onChange={(event) => setEditForm((current) => ({ ...current, good_examples: event.target.value }))} />
            </label>
            <label className="stack-xs">
              <span>Bad examples</span>
              <textarea className="input" rows={3} value={editForm.bad_examples} onChange={(event) => setEditForm((current) => ({ ...current, bad_examples: event.target.value }))} />
            </label>
            <button className="primary-button" disabled={isUpdating || !selectedBrandId} type="submit">
              {isUpdating ? 'Сохраняем…' : 'Обновить бренд'}
            </button>
          </form>
        </article>
      </section>
    </main>
  );
}
