'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { loadScopeSelection, loadSession } from '../../lib/auth';
import {
  exportContentPlans,
  generateContentPlans,
  getAudienceSegments,
  getBrands,
  getContentPlans,
  getOrganizations,
  getProducts,
} from '../../lib/api';
import type { AudienceSegmentRead, BrandRead, ContentPlanRead, OrganizationRead, ProductRead } from '../../lib/types';

const SCOPE_OPTIONS = [
  { value: 'brand', label: 'Бренд' },
  { value: 'product', label: 'Продукт' },
  { value: 'campaign', label: 'Кампания' },
  { value: 'comparison', label: 'Сравнение' },
] as const;

const PLATFORM_OPTIONS = ['инстаграм', 'линкедин', 'икс', 'тикток', 'ютуб', 'почта'] as const;
const CONTENT_TYPE_OPTIONS = ['пост', 'сторис', 'рилс', 'карусель', 'письмо', 'короткое видео'] as const;

type PlanGenerationFormState = {
  scope: 'brand' | 'product' | 'campaign' | 'comparison';
  product_id: string;
  audience_segment_id: string;
  start_date: string;
  end_date: string;
  title_prefix: string;
  platform: string;
  content_type: string;
  goal: string;
  status: string;
};

const EMPTY_FORM: PlanGenerationFormState = {
  scope: 'brand',
  product_id: '',
  audience_segment_id: '',
  start_date: '',
  end_date: '',
  title_prefix: 'Контент-план',
  platform: 'instagram',
  content_type: 'post',
  goal: '',
  status: 'draft',
};

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU');
}

export default function ContentPlansPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [brandId, setBrandId] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [segments, setSegments] = useState<AudienceSegmentRead[]>([]);
  const [plans, setPlans] = useState<ContentPlanRead[]>([]);
  const [selectedScope, setSelectedScope] = useState<'brand' | 'product' | 'campaign' | 'comparison'>('brand');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [selectedAudienceSegmentId, setSelectedAudienceSegmentId] = useState<string>('');
  const [form, setForm] = useState<PlanGenerationFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
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
        const [orgResponse, brandResponse, productResponse, segmentResponse] = await Promise.all([
          getOrganizations(token),
          getBrands(token, orgId),
          getProducts(token, orgId, brId),
          getAudienceSegments(token, orgId, brId),
        ]);
        if (cancelled) return;
        setOrganizations(orgResponse.items);
        setBrands(brandResponse.items);
        setProducts(productResponse.items);
        setSegments(segmentResponse.items);
        setSelectedProductId(productResponse.items[0]?.id ?? '');
        setSelectedAudienceSegmentId(segmentResponse.items[0]?.id ?? '');
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
    if (selectedScope !== 'product') {
      setSelectedProductId('');
    }
    if (!selectedAudienceSegmentId) {
      setSelectedAudienceSegmentId(segments[0]?.id ?? '');
    }
  }, [products, segments, selectedAudienceSegmentId, selectedProductId, selectedScope]);

  useEffect(() => {
    if (!accessToken || !organizationId || !brandId) {
      setPlans([]);
      return;
    }

    const token = accessToken as string;
    const orgId = organizationId as string;
    const brId = brandId as string;
    let cancelled = false;
    async function loadPlans() {
      try {
        const response = await getContentPlans(
          token,
          orgId,
          brId,
          selectedScope,
          selectedScope === 'product' ? selectedProductId || null : null,
          selectedAudienceSegmentId || null,
        );
        if (!cancelled) {
          setPlans(response.items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить контент-планы');
          setPlans([]);
        }
      }
    }

    loadPlans();

    return () => {
      cancelled = true;
    };
  }, [accessToken, brandId, organizationId, selectedAudienceSegmentId, selectedProductId, selectedScope]);

  const currentOrganization = organizationId ? organizations.find((item) => item.id === organizationId) ?? null : null;
  const currentBrand = brandId ? brands.find((item) => item.id === brandId) ?? null : null;
  const selectedProduct = selectedProductId ? products.find((item) => item.id === selectedProductId) ?? null : null;
  const selectedSegment = selectedAudienceSegmentId ? segments.find((item) => item.id === selectedAudienceSegmentId) ?? null : null;

  const productOptions = useMemo(
    () => products.map((product) => ({ id: product.id, label: `${product.sku} · ${product.name}` })),
    [products],
  );
  const segmentOptions = useMemo(
    () => segments.map((segment) => ({ id: segment.id, label: segment.name })),
    [segments],
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
    if (!form.start_date || !form.end_date) {
      setError('Укажи start_date и end_date');
      return;
    }

    const token = accessToken as string;
    const orgId = organizationId as string;
    const brId = brandId as string;

    setIsGenerating(true);
    setError(null);
    setNotice(null);

    try {
      const response = await generateContentPlans(token, {
        organization_id: orgId,
        brand_id: brId,
        product_id: selectedScope === 'product' ? selectedProductId : null,
        audience_segment_id: selectedAudienceSegmentId || null,
        scope: selectedScope,
        start_date: form.start_date,
        end_date: form.end_date,
        title_prefix: form.title_prefix.trim() || 'Контент-план',
        platform: form.platform.trim(),
        content_type: form.content_type.trim(),
        goal: form.goal.trim(),
        status: form.status.trim() || 'draft',
      });
      setNotice(`Сгенерировано контент-планов: ${response.items.length}`);
      setForm(EMPTY_FORM);
      const refreshed = await getContentPlans(
        token,
        orgId,
        brId,
        selectedScope,
        selectedScope === 'product' ? selectedProductId || null : null,
        selectedAudienceSegmentId || null,
      );
      setPlans(refreshed.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сгенерировать контент-планы');
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleExport() {
    if (!accessToken || !organizationId || !brandId) {
      setError('Нет активной области');
      return;
    }
    const token = accessToken as string;
    const orgId = organizationId as string;
    const brId = brandId as string;
    try {
      const response = await exportContentPlans(token, {
        organization_id: orgId,
        brand_id: brId,
        scope: selectedScope,
        product_id: selectedScope === 'product' ? selectedProductId || null : null,
        audience_segment_id: selectedAudienceSegmentId || null,
        format: 'csv',
      });
      const blob = new Blob([response.content], { type: response.contentType });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `content-plans-${orgId}-${brId}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice('Экспорт CSV готов');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось экспортировать контент-планы');
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Контент-планы</span>
          <h1>Генерация контент-планов</h1>
          <p className="muted">
            AI-генерация плана по методологии выбранной площадки: разные форматы и темы, воронка awareness→trust→sales, на основе Brand DNA, фактов товара и аудитории.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Панель</Link>
          <Link className="secondary-button" href="/products">Продукты</Link>
          <Link className="secondary-button" href="/subscriptions">Подписки</Link>
          <button className="primary-button" onClick={handleExport} type="button">
            Экспорт CSV
          </button>
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
            <div><dt>Режим области</dt><dd>{selectedScope === 'brand' ? 'Бренд' : selectedScope === 'product' ? 'Продукт' : selectedScope === 'campaign' ? 'Кампания' : 'Сравнение'}</dd></div>
            <div><dt>Продукт</dt><dd>{selectedProduct ? selectedProduct.name : '—'}</dd></div>
            <div><dt>Сегмент аудитории</dt><dd>{selectedSegment ? selectedSegment.name : '—'}</dd></div>
            <div><dt>Загружено планов</dt><dd>{plans.length}</dd></div>
          </dl>
        </article>

        <article className="card stack-sm">
          <h2>Что используется</h2>
          <ul className="checklist">
            <li>область, даты и контекст ДНК бренда/продукта</li>
            <li>область продукта требует идентификатор продукта</li>
            <li>результат сохраняется как строки контент-планов</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Сгенерировать планы</h2>
              <p className="muted">AI создаёт осмысленный план на период: подходящая частота для площадки, разные форматы (пост/reel/карусель/сторис/видео), у каждой строки — тема, тип и краткий бриф с хуком.</p>
            </div>
          </div>

          <form className="stack-md" onSubmit={handleSubmit}>
            <label className="label-stack">
              <span>Область</span>
              <select className="input" onChange={(event) => setSelectedScope(event.target.value as typeof selectedScope)} value={selectedScope}>
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

            <label className="label-stack">
              <span>Сегмент аудитории</span>
              <select className="input" disabled={segmentOptions.length === 0} onChange={(event) => setSelectedAudienceSegmentId(event.target.value)} value={selectedAudienceSegmentId}>
                {segmentOptions.length === 0 ? <option value="">Нет сегментов</option> : null}
                <option value="">Без сегмента</option>
                {segmentOptions.map((segment) => (
                  <option key={segment.id} value={segment.id}>{segment.label}</option>
                ))}
              </select>
            </label>

            <div className="grid two-up">
              <label className="label-stack"><span>Дата начала</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} required type="date" value={form.start_date} /></label>
              <label className="label-stack"><span>Дата окончания</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} required type="date" value={form.end_date} /></label>
            </div>

            <label className="label-stack"><span>Префикс названия</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, title_prefix: event.target.value }))} value={form.title_prefix} /></label>
            <label className="label-stack">
              <span>Платформа</span>
              <select className="input" onChange={(event) => setForm((current) => ({ ...current, platform: event.target.value }))} value={form.platform}>
                {PLATFORM_OPTIONS.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <label className="label-stack">
              <span>Тип контента</span>
              <select className="input" onChange={(event) => setForm((current) => ({ ...current, content_type: event.target.value }))} value={form.content_type}>
                {CONTENT_TYPE_OPTIONS.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <label className="label-stack"><span>Цель</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, goal: event.target.value }))} required rows={4} value={form.goal} /></label>
            <label className="label-stack"><span>Статус</span><select className="input" onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))} value={form.status}><option value="draft">черновик</option><option value="scheduled">запланирован</option><option value="published">опубликован</option><option value="archived">архив</option></select></label>

            <button className="primary-button" disabled={isGenerating} type="submit">
              {isGenerating ? 'Генерируем…' : 'Сгенерировать планы'}
            </button>
          </form>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Сгенерированные планы</h2>
              <p className="muted">Список актуальных контент-планов для выбранной области.</p>
            </div>
            <span className="pill">{plans.length}</span>
          </div>

          <div className="stack-sm">
            {plans.map((plan) => (
              <article className="brief-card stack-xs" key={plan.id}>
                <div className="brief-meta">
                  <strong>{plan.title}</strong>
                  <span className="pill subtle-pill">{plan.scope === 'brand' ? 'Бренд' : plan.scope === 'product' ? 'Продукт' : plan.scope === 'campaign' ? 'Кампания' : 'Сравнение'}</span>
                </div>
                <p className="brief-content">{plan.goal}</p>
                <dl className="keyvals">
                  <div><dt>Дата</dt><dd>{plan.date}</dd></div>
                  <div><dt>Platform</dt><dd>{plan.platform}</dd></div>
                  <div><dt>Тип контента</dt><dd>{plan.content_type}</dd></div>
                  <div><dt>Продукт</dt><dd>{plan.product_id ?? '—'}</dd></div>
                  <div><dt>Сегмент аудитории</dt><dd>{plan.audience_segment_id ?? '—'}</dd></div>
                  <div><dt>Статус</dt><dd>{plan.status === 'draft' ? 'черновик' : plan.status === 'scheduled' ? 'запланирован' : plan.status === 'published' ? 'опубликован' : plan.status === 'archived' ? 'архив' : plan.status}</dd></div>
                  <div><dt>Создан</dt><dd>{formatDateTime(plan.created_at)}</dd></div>
                </dl>
              </article>
            ))}
            {!isLoading && plans.length === 0 ? <p className="muted">Пока нет контент-планов в текущей области.</p> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
