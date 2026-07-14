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

function prettyList(items: string[] | null | undefined): string {
  return items && items.length > 0 ? items.join(', ') : '—';
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

function composeProductSummary(record: Record<string, unknown> | null): string | null {
  const parts = [
    readText(record, ['description', 'summary', 'positioning', 'value_proposition', 'overview', 'pitch']),
    readList(record, ['features', 'capabilities', 'benefits', 'advantages'])?.slice(0, 3).join(', '),
  ].filter((item): item is string => Boolean(item && item.trim()));

  if (parts.length) {
    return parts.join(' · ');
  }

  const anyText = findAnyTextDeep(record);
  if (!anyText) return null;
  return anyText.length > 180 ? `${anyText.slice(0, 177)}…` : anyText;
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
      setError('Сначала выбери организацию и бренд на панели');
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
  const dnaRecord = useMemo(() => getDnaRecord(selectedProduct?.dna_json ?? null), [selectedProduct]);

  useEffect(() => {
    if (!selectedProduct) {
      setForm(EMPTY_FORM);
      return;
    }

    setForm({
      sku: selectedProduct.sku,
      name: selectedProduct.name,
      category: selectedProduct.category,
      description: selectedProduct.description || readText(dnaRecord, ['description', 'summary', 'positioning', 'value_proposition']) || '',
      features: joinList(selectedProduct.features.length ? selectedProduct.features : readList(dnaRecord, ['features', 'capabilities']) ?? []),
      benefits: joinList(selectedProduct.benefits.length ? selectedProduct.benefits : readList(dnaRecord, ['benefits', 'advantages']) ?? []),
      proofs: joinList(selectedProduct.proofs.length ? selectedProduct.proofs : readList(dnaRecord, ['proofs', 'evidence', 'proof']) ?? []),
      objections: joinList(selectedProduct.objections.length ? selectedProduct.objections : readList(dnaRecord, ['objections', 'risks', 'concerns']) ?? []),
      restrictions: joinList(selectedProduct.restrictions.length ? selectedProduct.restrictions : readList(dnaRecord, ['restrictions', 'constraints', 'limitations']) ?? []),
      status: selectedProduct.status,
      readiness_score: String(selectedProduct.readiness_score),
    });
  }, [dnaRecord, selectedProduct]);

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
      setError('Нет активной области');
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
      setNotice('Задача на генерацию ДНК продукта создана');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить ДНК продукта');
    } finally {
      setIsGenerating(null);
    }
  }

  const scopeSummary = scope
    ? `${scope.organizationId}${scope.brandId ? ` · ${scope.brandId}` : ''}`
    : 'область не выбрана';

  const currentOrganization = scope?.organizationId
    ? organizations.find((item) => item.id === scope.organizationId) ?? null
    : null;
  const currentBrand = scope?.brandId ? brands.find((item) => item.id === scope.brandId) ?? null : null;

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Продукты</span>
          <h1>Продуктовый кабинет</h1>
          <p className="muted">
            Это первый вынос продукта из панели: список, карточка, редактирование и запуск ДНК продукта.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">
            Назад в панель
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
          <h2>Область</h2>
          <dl className="keyvals">
            <div>
              <dt>Организация</dt>
              <dd>{currentOrganization ? currentOrganization.name : scope?.organizationId ?? '—'}</dd>
            </div>
            <div>
              <dt>Бренд</dt>
              <dd>{currentBrand ? currentBrand.name : scope?.brandId ?? '—'}</dd>
            </div>
            <div>
              <dt>ID области</dt>
              <dd className="mono">{scopeSummary}</dd>
            </div>
            <div>
              <dt>Загружено продуктов</dt>
              <dd>{products.length}</dd>
            </div>
          </dl>
          <p className="muted">
            Если область пустая, сначала вернись в панель и выбери организацию и бренд.
          </p>
        </article>

        <article className="card stack-sm">
          <h2>Что уже доступно</h2>
          <ul className="checklist">
            <li>создать, посмотреть, обновить и запустить ДНК продукта</li>
            <li>архивная организация блокирует запись продуктов</li>
            <li>бренд и организация в форме фиксируются из области панели</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>{selectedProduct ? 'Редактировать продукт' : 'Создать продукт'}</h2>
              <p className="muted">Работаем только в выбранной области организации и бренда.</p>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="label-stack">
              <span>Артикул</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))} value={form.sku} required />
            </label>

            <label className="label-stack">
              <span>Название</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} value={form.name} required />
            </label>

            <label className="label-stack">
              <span>Категория</span>
              <input className="input" onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} value={form.category} required />
            </label>

            <label className="label-stack">
              <span>Описание</span>
              <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows={4} value={form.description} required />
            </label>

            <div className="grid two-up">
              <label className="label-stack">
                <span>Функции</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, features: event.target.value }))} rows={4} value={form.features} />
              </label>
              <label className="label-stack">
                <span>Преимущества</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, benefits: event.target.value }))} rows={4} value={form.benefits} />
              </label>
            </div>

            <div className="grid two-up">
              <label className="label-stack">
                <span>Доказательства</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, proofs: event.target.value }))} rows={4} value={form.proofs} />
              </label>
              <label className="label-stack">
                <span>Возражения</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, objections: event.target.value }))} rows={4} value={form.objections} />
              </label>
            </div>

            <div className="grid two-up">
              <label className="label-stack">
                <span>Ограничения</span>
                <textarea className="input" onChange={(event) => setForm((current) => ({ ...current, restrictions: event.target.value }))} rows={3} value={form.restrictions} />
              </label>
              <label className="label-stack">
                <span>Оценка готовности</span>
                <input className="input" min="0" max="100" onChange={(event) => setForm((current) => ({ ...current, readiness_score: event.target.value }))} type="number" value={form.readiness_score} />
              </label>
            </div>

            <label className="label-stack">
              <span>Статус</span>
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
              <p className="muted">Выбери строку, чтобы отредактировать или запустить ДНК-задачу.</p>
            </div>
          </div>

          {selectedProduct ? (
            <div className="card stack-sm subtle-card">
              <div className="keyvals">
                <div><dt>Название</dt><dd>{selectedProduct.name}</dd></div>
                <div><dt>Артикул</dt><dd>{selectedProduct.sku}</dd></div>
                <div><dt>Категория</dt><dd>{selectedProduct.category}</dd></div>
                <div><dt>Описание</dt><dd>{selectedProduct.description || readText(dnaRecord, ['description', 'summary', 'positioning', 'value_proposition']) || '—'}</dd></div>
                <div><dt>Статус</dt><dd>{selectedProduct.status}</dd></div>
                <div><dt>Готовность</dt><dd>{selectedProduct.readiness_score}/100</dd></div>
              </div>

              <div className="row-label">Функции</div>
              <p>{prettyList(selectedProduct.features.length ? selectedProduct.features : readList(dnaRecord, ['features', 'capabilities']))}</p>
              <div className="row-label">Преимущества</div>
              <p>{prettyList(selectedProduct.benefits.length ? selectedProduct.benefits : readList(dnaRecord, ['benefits', 'advantages']))}</p>
              <div className="row-label">Доказательства</div>
              <p>{prettyList(selectedProduct.proofs.length ? selectedProduct.proofs : readList(dnaRecord, ['proofs', 'evidence', 'proof']))}</p>
              <div className="row-label">Возражения</div>
              <p>{prettyList(selectedProduct.objections.length ? selectedProduct.objections : readList(dnaRecord, ['objections', 'risks', 'concerns']))}</p>
              <div className="row-label">Ограничения</div>
              <p>{prettyList(selectedProduct.restrictions.length ? selectedProduct.restrictions : readList(dnaRecord, ['restrictions', 'constraints', 'limitations']))}</p>

              <div className="row-label">Ключевой вывод</div>
              <p>{composeProductSummary(dnaRecord) ?? 'Данные продукта пока не заполнены'}</p>

              <details>
                <summary>Показать технические данные</summary>
                <pre className="code-block">{selectedProduct.dna_json ? JSON.stringify(selectedProduct.dna_json, null, 2) : 'Product DNA ещё не сгенерирован'}</pre>
              </details>
            </div>
          ) : null}

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
                  <p className="muted">{product.category} · готовность {product.readiness_score}/100</p>
                  <p className="muted">{product.description}</p>
                  <p className="row-label">Создан {formatDateTime(product.created_at)}</p>
                </div>
                <div className="stack-sm">
                  <button className="secondary-button" onClick={() => setSelectedProductId(product.id)} type="button">
                    Редактировать
                  </button>
                  <button className="secondary-button" disabled={isGenerating === product.id} onClick={() => handleGenerateDna(product.id)} type="button">
                    {isGenerating === product.id ? 'ДНК…' : 'Сгенерировать ДНК'}
                  </button>
                </div>
              </div>
            ))}
            {!isLoading && products.length === 0 ? <p className="muted">Пока нет продуктов в выбранной области.</p> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
