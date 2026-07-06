'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { loadScopeSelection, loadSession } from '../../lib/auth';
import {
  createMediaAsset,
  getBrands,
  getMediaAssets,
  getOrganizations,
  getProducts,
} from '../../lib/api';
import type { BrandRead, MediaAssetRead, OrganizationRead, ProductRead } from '../../lib/types';

const SCOPE_OPTIONS = [
  { value: 'brand', label: 'Brand' },
  { value: 'product', label: 'Product' },
] as const;

type MediaAssetFormState = {
  scope: 'brand' | 'product';
  product_id: string;
  name: string;
  description: string;
  asset_key: string;
  source_url: string;
  content_type: string;
  size_bytes: string;
  checksum: string;
};

const EMPTY_FORM: MediaAssetFormState = {
  scope: 'brand',
  product_id: '',
  name: '',
  description: '',
  asset_key: '',
  source_url: '',
  content_type: 'image/png',
  size_bytes: '',
  checksum: '',
};

function splitTags(value: string): string[] {
  return value
    .split('\n')
    .flatMap((line) => line.split(','))
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU');
}

export default function MediaAssetsPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [brandId, setBrandId] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [assets, setAssets] = useState<MediaAssetRead[]>([]);
  const [selectedScope, setSelectedScope] = useState<'brand' | 'product'>('brand');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [form, setForm] = useState<MediaAssetFormState>(EMPTY_FORM);
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
      setError('Сначала выбери organization и brand на dashboard');
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
      setAssets([]);
      return;
    }

    const token = accessToken as string;
    const orgId = organizationId as string;
    const brId = brandId as string;
    let cancelled = false;

    async function load() {
      try {
        const response = await getMediaAssets(
          token,
          orgId,
          brId,
          selectedScope,
          selectedScope === 'product' ? selectedProductId || null : null,
        );
        if (!cancelled) {
          setAssets(response.items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить медиа');
          setAssets([]);
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
      setError('Нет активного scope');
      return;
    }
    if (selectedScope === 'product' && !selectedProductId) {
      setError('Для product scope нужен product_id');
      return;
    }

    setIsSaving(true);
    setError(null);
    setNotice(null);

    try {
      const saved = await createMediaAsset(accessToken, {
        organization_id: organizationId,
        brand_id: brandId,
        product_id: selectedScope === 'product' ? selectedProductId : null,
        scope: selectedScope,
        name: form.name.trim(),
        description: form.description.trim(),
        asset_key: form.asset_key.trim(),
        source_url: form.source_url.trim() || null,
        content_type: form.content_type.trim(),
        size_bytes: form.size_bytes.trim() ? Number(form.size_bytes) : null,
        checksum: form.checksum.trim() || null,
      });
      setNotice(`Media asset создан: ${saved.name}`);
      setForm(EMPTY_FORM);
      const response = await getMediaAssets(
        accessToken,
        organizationId,
        brandId,
        selectedScope,
        selectedScope === 'product' ? selectedProductId || null : null,
      );
      setAssets(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить медиа asset');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Media library</span>
          <h1>Библиотека медиа</h1>
          <p className="muted">
            Первый медиа-срез: brand/product scope, список ассетов и создание записи в live API.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Dashboard</Link>
          <Link className="secondary-button" href="/products">Products</Link>
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
            <div><dt>Organization</dt><dd>{currentOrganization ? currentOrganization.name : organizationId ?? '—'}</dd></div>
            <div><dt>Brand</dt><dd>{currentBrand ? currentBrand.name : brandId ?? '—'}</dd></div>
            <div><dt>Scope mode</dt><dd>{selectedScope}</dd></div>
            <div><dt>Product</dt><dd>{selectedProduct ? selectedProduct.name : '—'}</dd></div>
            <div><dt>Assets loaded</dt><dd>{assets.length}</dd></div>
          </dl>
        </article>

        <article className="card stack-sm">
          <h2>Что доступно</h2>
          <ul className="checklist">
            <li>чтение media-assets по current org/brand scope</li>
            <li>запись media asset через live API</li>
            <li>product scope поддерживается через опциональный product_id</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Создать media asset</h2>
              <p className="muted">Brand-level или product-level запись с проверкой scope.</p>
            </div>
          </div>

          <form className="stack-md" onSubmit={handleSubmit}>
            <label className="label-stack">
              <span>Scope</span>
              <select className="input" onChange={(event) => setSelectedScope(event.target.value as 'brand' | 'product')} value={selectedScope}>
                {SCOPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>

            <label className="label-stack">
              <span>Product</span>
              <select className="input" disabled={selectedScope !== 'product' || productOptions.length === 0} onChange={(event) => setSelectedProductId(event.target.value)} value={selectedProductId}>
                {selectedScope === 'product' && productOptions.length === 0 ? <option value="">Нет продуктов</option> : null}
                <option value="">{selectedScope === 'product' ? 'Выбери product' : 'Brand scope — product не нужен'}</option>
                {productOptions.map((product) => (
                  <option key={product.id} value={product.id}>{product.label}</option>
                ))}
              </select>
            </label>

            <label className="label-stack"><span>Name</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required value={form.name} /></label>
            <label className="label-stack"><span>Description</span><textarea className="input" onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows={3} required value={form.description} /></label>
            <label className="label-stack"><span>Asset key</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, asset_key: event.target.value }))} required value={form.asset_key} /></label>
            <label className="label-stack"><span>Source URL</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, source_url: event.target.value }))} value={form.source_url} /></label>
            <label className="label-stack"><span>Content type</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, content_type: event.target.value }))} required value={form.content_type} /></label>
            <div className="grid two-up">
              <label className="label-stack"><span>Size bytes</span><input className="input" inputMode="numeric" onChange={(event) => setForm((current) => ({ ...current, size_bytes: event.target.value }))} value={form.size_bytes} /></label>
              <label className="label-stack"><span>Checksum</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, checksum: event.target.value }))} value={form.checksum} /></label>
            </div>

            <button className="primary-button" disabled={isSaving} type="submit">
              {isSaving ? 'Сохраняем…' : 'Создать media asset'}
            </button>
          </form>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Media assets</h2>
              <p className="muted">Список текущих ассетов для выбранного scope.</p>
            </div>
            <span className="pill">{assets.length}</span>
          </div>

          <div className="stack-sm">
            {assets.map((asset) => (
              <article className="brief-card stack-xs" key={asset.id}>
                <div className="brief-meta">
                  <strong>{asset.name}</strong>
                  <span className="pill subtle-pill">{asset.scope}</span>
                </div>
                <p className="brief-content">{asset.description}</p>
                <dl className="keyvals">
                  <div><dt>Asset key</dt><dd className="mono">{asset.asset_key}</dd></div>
                  <div><dt>Content type</dt><dd>{asset.content_type}</dd></div>
                  <div><dt>Product</dt><dd>{asset.product_id ?? '—'}</dd></div>
                  <div><dt>Created</dt><dd>{formatDateTime(asset.created_at)}</dd></div>
                </dl>
              </article>
            ))}
            {!isLoading && assets.length === 0 ? <p className="muted">Пока нет media assets в текущем scope.</p> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
