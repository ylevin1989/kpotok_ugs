'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { loadScopeSelection, loadSession } from '../../lib/auth';
import { generateBrandDna, getBrands, getOrganizations } from '../../lib/api';
import type { BrandRead, OrganizationRead } from '../../lib/types';

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU');
}

export default function BrandsPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState<string | null>(null);
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
        const [orgResponse, brandResponse] = await Promise.all([
          getOrganizations(token),
          getBrands(token, orgId),
        ]);
        if (cancelled) {
          return;
        }
        setOrganizations(orgResponse.items);
        setBrands(brandResponse.items);
        setSelectedBrandId(brandResponse.items[0]?.id ?? null);
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

  const selectedBrand = useMemo(
    () => brands.find((brand) => brand.id === selectedBrandId) ?? null,
    [brands, selectedBrandId],
  );

  const currentOrganization = organizationId
    ? organizations.find((item) => item.id === organizationId) ?? null
    : null;

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

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Brands</span>
          <h1>Брендовый кабинет</h1>
          <p className="muted">
            Здесь живёт первый брендовый slice: список брендов в текущем organization scope и запуск Brand DNA.
          </p>
        </div>
        <Link className="secondary-button" href="/dashboard">
          Назад в dashboard
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
          <h2>Scope</h2>
          <dl className="keyvals">
            <div>
              <dt>Organization</dt>
              <dd>{currentOrganization ? currentOrganization.name : organizationId ?? '—'}</dd>
            </div>
            <div>
              <dt>Brands loaded</dt>
              <dd>{brands.length}</dd>
            </div>
          </dl>
        </article>

        <article className="card stack-sm">
          <h2>Что уже доступно</h2>
          <ul className="checklist">
            <li>brand list читается из live API</li>
            <li>Brand DNA job можно запускать прямо отсюда</li>
            <li>организация берётся из dashboard scope</li>
          </ul>
        </article>
      </section>

      <section className="grid two-up">
        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Список брендов</h2>
              <p className="muted">Выбери бренд, чтобы увидеть карточку справа.</p>
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
                    <span className="pill">{brand.dna_json ? 'DNA ready' : 'DNA empty'}</span>
                  </div>
                  <p className="row-label">Created {formatDateTime(brand.created_at)}</p>
                </div>
                <div className="stack-sm">
                  <button className="secondary-button" onClick={() => setSelectedBrandId(brand.id)} type="button">
                    Open
                  </button>
                  <button className="secondary-button" disabled={isGenerating === brand.id} onClick={() => handleGenerateDna(brand.id)} type="button">
                    {isGenerating === brand.id ? 'DNA…' : 'Generate DNA'}
                  </button>
                </div>
              </div>
            ))}
            {!isLoading && brands.length === 0 ? <p className="muted">Пока нет брендов в выбранном organization scope.</p> : null}
          </div>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <div>
              <h2>Карточка бренда</h2>
              <p className="muted">Быстрый просмотр текущего brand DNA payload.</p>
            </div>
          </div>

          {selectedBrand ? (
            <div className="stack-sm">
              <dl className="keyvals">
                <div>
                  <dt>Name</dt>
                  <dd>{selectedBrand.name}</dd>
                </div>
                <div>
                  <dt>Slug</dt>
                  <dd>{selectedBrand.slug}</dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd>{formatDateTime(selectedBrand.updated_at)}</dd>
                </div>
              </dl>

              <pre className="code-block">{selectedBrand.dna_json ? JSON.stringify(selectedBrand.dna_json, null, 2) : 'Brand DNA ещё не сгенерирован'}</pre>
            </div>
          ) : (
            <p className="muted">Выбери бренд слева, чтобы увидеть детали.</p>
          )}
        </article>
      </section>
    </main>
  );
}
