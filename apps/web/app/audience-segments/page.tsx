'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { loadScopeSelection, loadSession } from '../../lib/auth';
import {
  createAudienceSegment,
  getAudienceSegments,
  getBrands,
  getOrganizations,
  getProducts,
} from '../../lib/api';
import type { AudienceSegmentRead, BrandRead, OrganizationRead, ProductRead } from '../../lib/types';

const SCOPE_OPTIONS = [
  { value: 'brand', label: 'Бренд' },
  { value: 'product', label: 'Продукт' },
] as const;

type AudienceSegmentFormState = {
  scope: 'brand' | 'product';
  product_id: string;
  name: string;
  description: string;
  pain_points: string;
  goals: string;
  objections: string;
  keywords: string;
};

const EMPTY_FORM: AudienceSegmentFormState = {
  scope: 'brand',
  product_id: '',
  name: '',
  description: '',
  pain_points: '',
  goals: '',
  objections: '',
  keywords: '',
};

function splitList(value: string): string[] {
  return value
    .split('\n')
    .flatMap((line) => line.split(','))
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinList(items: string[]): string {
  return items.join(', ');
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU');
}

export default function AudienceSegmentsPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [brandId, setBrandId] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [segments, setSegments] = useState<AudienceSegmentRead[]>([]);
  const [selectedScope, setSelectedScope] = useState<'brand' | 'product'>('brand');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [form, setForm] = useState<AudienceSegmentFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const session = loadSession();
    if (!session) {
      router.replace('/login');
      return;
    }

    const scope = loadScopeSelection();
    if (!scope?.organizationId || !scope.brandId) {
      setError('Сначала выбери организацию и бренд на панели');
      setIsLoading(false);
      return;
    }

    const token = session.accessToken;
    const orgId = scope.organizationId;
    const brId = scope.brandId;
    setAccessToken(token);
    setOrganizationId(orgId);
    setBrandId(brId);

    let cancelled = false;

    async function bootstrap() {
      try {
        const [orgResponse, brandResponse, productResponse] = await Promise.all([
          getOrganizations(token),
          getBrands(token, orgId),
          getProducts(token, orgId, brId),
        ]);
        if (cancelled) return;
        setOrganizations(orgResponse.items);
        setBrands(brandResponse.items);
        setProducts(productResponse.items);
        setSelectedProductId(productResponse.items[0]?.id ?? '');
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить справочники');
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
    if (selectedScope === 'product' && !selectedProductId) {
      setSelectedProductId(products[0]?.id ?? '');
    }
    if (selectedScope === 'brand') {
      setSelectedProductId('');
    }
  }, [products, selectedProductId, selectedScope]);

  useEffect(() => {
    if (!accessToken || !organizationId || !brandId) {
      setSegments([]);
      return;
    }

    const token = accessToken as string;
    const orgId = organizationId as string;
    const brId = brandId as string;
    let cancelled = false;

    async function load() {
      try {
        const response = await getAudienceSegments(
          token,
          orgId,
          brId,
          selectedScope,
          selectedScope === 'product' ? selectedProductId || null : null,
        );
        if (!cancelled) {
          setSegments(response.items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить audience segments');
          setSegments([]);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [accessToken, brandId, organizationId, selectedProductId, selectedScope]);

  const currentOrganization = organizationId ? organizations.find((item) => item.id === organizationId) ?? null : null;
  const currentBrand = brandId ? brands.find((item) => item.id === brandId) ?? null : null;
  const selectedProduct = selectedProductId ? products.find((item) => item.id === selectedProductId) ?? null : null;
  const productOptions = useMemo(
    () => products.map((product) => ({ id: product.id, label: `${product.sku} · ${product.name}` })),
    [products],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !organizationId || !brandId) {
      setError('Нет активной области');
      return;
    }
    if (selectedScope === 'product' && !selectedProductId) {
      setError('Для области продукта нужен идентификатор продукта');
      return;
    }

    setIsSaving(true);
    setError(null);
    setNotice(null);

    try {
      const saved = await createAudienceSegment(accessToken, {
        organization_id: organizationId,
        brand_id: brandId,
        product_id: selectedScope === 'product' ? selectedProductId : null,
        scope: selectedScope,
        name: form.name.trim(),
        description: form.description.trim(),
        pain_points: splitList(form.pain_points),
        goals: splitList(form.goals),
        objections: splitList(form.objections),
        keywords: splitList(form.keywords),
      });
      setNotice(`Сегмент аудитории создан: ${saved.name}`);
      setForm(EMPTY_FORM);
      const response = await getAudienceSegments(
        accessToken,
        organizationId,
        brandId,
        selectedScope,
        selectedScope === 'product' ? selectedProductId || null : null,
      );
      setSegments(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить сегмент аудитории');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Сегменты аудитории</span>
          <h1>Сегменты аудитории</h1>
          <p className="muted">
            Аудитории с учётом бренда и продукта: список, запись в live API и поддержка области продукта.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Панель</Link>
          <Link className="secondary-button" href="/products">Продукты</Link>
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
          <h2>Область</h2>
          <dl className="keyvals">
            <div><dt>Организация</dt><dd>{currentOrganization ? currentOrganization.name : organizationId ?? '—'}</dd></div>
            <div><dt>Бренд</dt><dd>{currentBrand ? currentBrand.name : brandId ?? '—'}</dd></div>
            <div><dt>Режим области</dt><dd>{selectedScope}</dd></div>
            <div><dt>Продукт</dt><dd>{selectedProduct ? selectedProduct.name : '—'}</dd></div>
            <div><dt>Загружено сегментов</dt><dd>{segments.length}</dd></div>
          </dl>
        </article>

        <article className="card stack-sm">
          <h2>Что доступно</h2>
          <ul className="checklist">
            <li>чтение сегментов аудитории по текущей области организации и бренда</li>
            <li>запись сегмента аудитории через live API</li>
            <li>область продукта поддерживается через необязательный идентификатор продукта</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Создать сегмент аудитории</h2>
              <p className="muted">Брендовый или продуктовый сегмент для генерации контента.</p>
            </div>
          </div>

          <form className="stack-md" onSubmit={handleSubmit}>
            <label className="label-stack">
              <span>Область</span>
              <select className="input" onChange={(event) => setSelectedScope(event.target.value as 'brand' | 'product')} value={selectedScope}>
                {SCOPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>

            <label className="label-stack">
              <span>Продукт</span>
              <select className="input" disabled={selectedScope !== 'product' || productOptions.length === 0} onChange={(event) => setSelectedProductId(event.target.value)} value={selectedProductId}>
                {selectedScope === 'product' && productOptions.length === 0 ? <option value="">Нет продуктов</option> : null}
                <option value="">{selectedScope === 'product' ? 'Выбери продукт' : 'Область бренда — продукт не нужен'}</option>
                {productOptions.map((product) => (
                  <option key={product.id} value={product.id}>{product.label}</option>
                ))}
              </select>
            </label>

            <label className="label-stack"><span>Название</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required value={form.name} /></label>
            <label className="label-stack"><span>Описание</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows={3} required value={form.description} /></label>
            <label className="label-stack"><span>Боли</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, pain_points: event.target.value }))} rows={4} value={form.pain_points} /></label>
            <label className="label-stack"><span>Цели</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, goals: event.target.value }))} rows={4} value={form.goals} /></label>
            <label className="label-stack"><span>Возражения</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, objections: event.target.value }))} rows={4} value={form.objections} /></label>
            <label className="label-stack"><span>Ключевые слова</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, keywords: event.target.value }))} rows={4} value={form.keywords} /></label>

            <button className="primary-button" disabled={isSaving} type="submit">
              {isSaving ? 'Сохраняем…' : 'Создать сегмент аудитории'}
            </button>
          </form>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Сегменты аудитории</h2>
              <p className="muted">Список текущих сегментов для выбранной области.</p>
            </div>
            <span className="pill">{segments.length}</span>
          </div>

          <div className="stack-sm">
            {segments.map((segment) => (
              <article className="brief-card stack-xs" key={segment.id}>
                <div className="brief-meta">
                  <strong>{segment.name}</strong>
                  <span className="pill subtle-pill">{segment.scope === 'brand' ? 'Бренд' : 'Продукт'}</span>
                </div>
                <p className="brief-content">{segment.description}</p>
                <dl className="keyvals">
                  <div><dt>Боли</dt><dd>{joinList(segment.pain_points) || '—'}</dd></div>
                  <div><dt>Цели</dt><dd>{joinList(segment.goals) || '—'}</dd></div>
                  <div><dt>Возражения</dt><dd>{joinList(segment.objections) || '—'}</dd></div>
                  <div><dt>Ключевые слова</dt><dd>{joinList(segment.keywords) || '—'}</dd></div>
                  <div><dt>Продукт</dt><dd>{segment.product_id ?? '—'}</dd></div>
                  <div><dt>Создан</dt><dd>{formatDateTime(segment.created_at)}</dd></div>
                </dl>
              </article>
            ))}
            {!isLoading && segments.length === 0 ? <p className="muted">Пока нет сегментов аудитории в текущей области.</p> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
