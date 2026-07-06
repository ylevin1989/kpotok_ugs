'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { clearSession, loadScopeSelection, loadSession } from '../../lib/auth';
import {
  createProduct,
  generateProductDna,
  getBrands,
  getOrganizations,
  getProducts,
  updateProduct,
} from '../../lib/api';
import type { BrandRead, OrganizationRead, ProductRead } from '../../lib/types';

type ProductFormState = {
  sku: string;
  name: string;
  category: string;
  description: string;
  features: string;
  benefits: string;
  proofs: string;
  objections: string;
  restrictions: string;
  status: string;
  readiness_score: string;
};

const EMPTY_FORM: ProductFormState = {
  sku: '',
  name: '',
  category: '',
  description: '',
  features: '',
  benefits: '',
  proofs: '',
  objections: '',
  restrictions: '',
  status: 'draft',
  readiness_score: '0',
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

export default function ProductsPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [scope, setScope] = useState<{ organizationId: string; brandId: string | null } | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [form, setForm] = useState<ProductFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const session = loadSession();
    if (!session) {
      router.replace('/login');
      return;
    }

    const savedScope = loadScopeSelection();
    const token = session.accessToken;
    setAccessToken(token);
    setScope(savedScope);
    if (!savedScope?.organizationId) {
      setError('Сначала выбери organization и brand на dashboard');
      setIsLoading(false);
      return;
    }

    const organizationId = savedScope.organizationId;
    let cancelled = false;

    async function bootstrap() {
      try {
        const [orgResponse, brandResponse] = await Promise.all([
          getOrganizations(token),
          getBrands(token, organizationId),
        ]);
        if (cancelled) {
          return;
        }
        setOrganizations(orgResponse.items);
        setBrands(brandResponse.items);
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
    if (!accessToken || !scope?.organizationId || !scope.brandId) {
      setProducts([]);
      return;
    }

    const token = accessToken as string;
    const organizationId = scope.organizationId;
    const brandId = scope.brandId as string;

    let cancelled = false;
    setIsLoading(true);

    async function load() {
      try {
        const response = await getProducts(token, organizationId, brandId);
        if (cancelled) {
          return;
        }
        setProducts(response.items);
        setSelectedProductId((current) => {
          if (current && response.items.some((item) => item.id === current)) {
            return current;
          }
          return response.items[0]?.id ?? null;
        });
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить продукты');
          setProducts([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [accessToken, scope?.brandId, scope?.organizationId]);

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId) ?? null,
    [products, selectedProductId],
  );

  useEffect(() => {
    if (!selectedProduct) {
      setForm(EMPTY_FORM);
      return;
    }

    setForm({
      sku: selectedProduct.sku,
      name: selectedProduct.name,
      category: selectedProduct.category,
      description: selectedProduct.description,
      features: joinList(selectedProduct.features),
      benefits: joinList(selectedProduct.benefits),
      proofs: joinList(selectedProduct.proofs),
      objections: joinList(selectedProduct.objections),
      restrictions: joinList(selectedProduct.restrictions),
      status: selectedProduct.status,
      readiness_score: String(selectedProduct.readiness_score),
    });
  }, [selectedProduct]);

  async function refreshProducts(nextSelectedId: string | null = selectedProductId) {
    if (!accessToken || !scope?.organizationId || !scope.brandId) {
      return;
    }
    const response = await getProducts(accessToken, scope.organizationId, scope.brandId);
    setProducts(response.items);
    if (nextSelectedId && response.items.some((item) => item.id === nextSelectedId)) {
      setSelectedProductId(nextSelectedId);
      return;
    }
    setSelectedProductId(response.items[0]?.id ?? null);
  }

  function handleReset() {
    setSelectedProductId(null);
    setForm(EMPTY_FORM);
    setNotice(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !scope?.organizationId || !scope.brandId) {
      setError('Нет активного scope');
      return;
    }

    setIsSaving(true);
    setError(null);
    setNotice(null);

    const payload = {
      organization_id: scope.organizationId,
      brand_id: scope.brandId,
      sku: form.sku.trim(),
      name: form.name.trim(),
      category: form.category.trim(),
      description: form.description.trim(),
      features: splitList(form.features),
      benefits: splitList(form.benefits),
      proofs: splitList(form.proofs),
      objections: splitList(form.objections),
      restrictions: splitList(form.restrictions),
      status: form.status.trim() || 'draft',
      readiness_score: Number(form.readiness_score || '0'),
    };

    try {
      const saved = selectedProductId
        ? await updateProduct(accessToken, selectedProductId, payload)
        : await createProduct(accessToken, payload);
      setNotice(selectedProductId ? 'Продукт обновлён' : 'Продукт создан');
      await refreshProducts(saved.id);
      setSelectedProductId(saved.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить продукт');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleGenerateDna(productId: string) {
    if (!accessToken) {
      return;
    }
    setIsGenerating(productId);
    setError(null);
    setNotice(null);
    try {
      await generateProductDna(accessToken, productId);
      setNotice('Job на генерацию Product DNA создан');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить Product DNA');
    } finally {
      setIsGenerating(null);
    }
  }

  const scopeSummary = scope
    ? `${scope.organizationId}${scope.brandId ? ` · ${scope.brandId}` : ''}`
    : 'scope не выбран';

  const currentOrganization = scope?.organizationId
    ? organizations.find((item) => item.id === scope.organizationId) ?? null
    : null;
  const currentBrand = scope?.brandId ? brands.find((item) => item.id === scope.brandId) ?? null : null;

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Products</span>
          <h1>Продуктовый кабинет</h1>
          <p className="muted">
            Это первый вынос продукта из dashboard: список, карточка, редактирование и запуск Product DNA.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">
            Назад в dashboard
          </Link>
          <button className="secondary-button" onClick={handleReset} type="button">
            Новый продукт
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
          <h2>Scope</h2>
          <dl className="keyvals">
            <div>
              <dt>Organization</dt>
              <dd>{currentOrganization ? currentOrganization.name : scope?.organizationId ?? '—'}</dd>
            </div>
            <div>
              <dt>Brand</dt>
              <dd>{currentBrand ? currentBrand.name : scope?.brandId ?? '—'}</dd>
            </div>
            <div>
              <dt>Scope id</dt>
              <dd className="mono">{scopeSummary}</dd>
            </div>
            <div>
              <dt>Products loaded</dt>
              <dd>{products.length}</dd>
            </div>
          </dl>
          <p className="muted">
            Если scope пустой, сначала вернись в dashboard и выбери organization/brand.
          </p>
        </article>

        <article className="card stack-sm">
          <h2>Что уже доступно</h2>
          <ul className="checklist">
            <li>create / list / update / generate-dna для products</li>
            <li>архивная organization блокирует product writes</li>
            <li>бренд и organization в форме фиксируются из dashboard scope</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>{selectedProduct ? 'Редактировать продукт' : 'Создать продукт'}</h2>
              <p className="muted">Работаем только в выбранном organization/brand scope.</p>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="label-stack">
              <span>SKU</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))} value={form.sku} required />
            </label>

            <label className="label-stack">
              <span>Name</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} value={form.name} required />
            </label>

            <label className="label-stack">
              <span>Category</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} value={form.category} required />
            </label>

            <label className="label-stack">
              <span>Description</span>
              <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows={4} value={form.description} required />
            </label>

            <div className="grid two-up">
              <label className="label-stack">
                <span>Features</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, features: event.target.value }))} rows={4} value={form.features} />
              </label>
              <label className="label-stack">
                <span>Benefits</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, benefits: event.target.value }))} rows={4} value={form.benefits} />
              </label>
            </div>

            <div className="grid two-up">
              <label className="label-stack">
                <span>Proofs</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, proofs: event.target.value }))} rows={4} value={form.proofs} />
              </label>
              <label className="label-stack">
                <span>Objections</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, objections: event.target.value }))} rows={4} value={form.objections} />
              </label>
            </div>

            <div className="grid two-up">
              <label className="label-stack">
                <span>Restrictions</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, restrictions: event.target.value }))} rows={3} value={form.restrictions} />
              </label>
              <label className="label-stack">
                <span>Readiness score</span>
                <input className="input" min="0" max="100" onChange={(event) => setForm((current) => ({ ...current, readiness_score: event.target.value }))} type="number" value={form.readiness_score} />
              </label>
            </div>

            <label className="label-stack">
              <span>Status</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))} value={form.status} />
            </label>

            <div className="row">
              <button className="primary-button" disabled={isSaving} type="submit">
                {isSaving ? 'Сохраняем…' : selectedProduct ? 'Обновить продукт' : 'Создать продукт'}
              </button>
              {selectedProduct ? (
                <button className="secondary-button" onClick={handleReset} type="button">
                  Отменить редактирование
                </button>
              ) : null}
            </div>
          </form>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Список продуктов</h2>
              <p className="muted">Выбери строку, чтобы отредактировать или запустить DNA job.</p>
            </div>
          </div>

          {isLoading ? <p className="muted">Загружаем данные…</p> : null}

          <div className="table-like">
            {products.map((product) => (
              <div className="row" key={product.id}>
                <div className="stack-sm" style={{ flex: 1 }}>
                  <div className="row">
                    <div>
                      <div className="row-label">{product.sku}</div>
                      <div className="row-value">{product.name}</div>
                    </div>
                    <span className="pill">{product.status}</span>
                  </div>
                  <p className="muted">{product.category} · readiness {product.readiness_score}/100</p>
                  <p className="muted">{product.description}</p>
                  <p className="row-label">Created {formatDateTime(product.created_at)}</p>
                </div>
                <div className="stack-sm">
                  <button className="secondary-button" onClick={() => setSelectedProductId(product.id)} type="button">
                    Edit
                  </button>
                  <button className="secondary-button" disabled={isGenerating === product.id} onClick={() => handleGenerateDna(product.id)} type="button">
                    {isGenerating === product.id ? 'DNA…' : 'Generate DNA'}
                  </button>
                </div>
              </div>
            ))}
            {!isLoading && products.length === 0 ? <p className="muted">Пока нет продуктов в выбранном scope.</p> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
