'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { clearScopeSelection, clearSession, loadScopeSelection, loadSession, saveScopeSelection } from '../../lib/auth';
import {
  getAudienceSegments,
  getBriefs,
  getBrands,
  getContentPlans,
  getJobs,
  getOrganizations,
  getProducts,
  getMe,
} from '../../lib/api';
import type {
  AudienceSegmentRead,
  BrandRead,
  BriefRead,
  JobRead,
  MeResponse,
  OrganizationRead,
  ProductRead,
  ContentPlanRead,
} from '../../lib/types';

function formatCount(count: number): string {
  return count === 0 ? '0' : String(count);
}

function formatStatus(total: number): string {
  if (total === 0) return 'empty';
  if (total === 1) return 'ready';
  return 'ready';
}

export default function ProductionFlowPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [data, setData] = useState<MeResponse | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [segments, setSegments] = useState<AudienceSegmentRead[]>([]);
  const [plans, setPlans] = useState<ContentPlanRead[]>([]);
  const [briefs, setBriefs] = useState<BriefRead[]>([]);
  const [jobs, setJobs] = useState<JobRead[]>([]);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState('');
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedBriefId, setSelectedBriefId] = useState('');
  const [selectedJobId, setSelectedJobId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isBrandsLoading, setIsBrandsLoading] = useState(false);
  const [isScopeLoading, setIsScopeLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const session = loadSession();
    if (!session) {
      router.replace('/login');
      return;
    }

    const token = session.accessToken;
    setAccessToken(token);
    let cancelled = false;

    async function bootstrap() {
      try {
        const [me, orgResponse] = await Promise.all([getMe(token), getOrganizations(token)]);
        if (cancelled) return;

        const orgItems = orgResponse.items;
        const savedScope = loadScopeSelection();
        const nextOrganizationId =
          savedScope && orgItems.some((item) => item.id === savedScope.organizationId)
            ? savedScope.organizationId
            : (orgItems[0]?.id ?? '');

        setData(me);
        setOrganizations(orgItems);
        setSelectedOrganizationId(nextOrganizationId);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить профиль');
          clearScopeSelection();
          clearSession();
          router.replace('/login');
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
    if (!accessToken || !selectedOrganizationId) {
      setBrands([]);
      setSelectedBrandId('');
      setProducts([]);
      setSegments([]);
      setPlans([]);
      setBriefs([]);
      setJobs([]);
      setSelectedBriefId('');
      setSelectedJobId('');
      return;
    }

    const token = accessToken;
    let cancelled = false;
    setIsBrandsLoading(true);

    async function loadScope() {
      try {
        const brandResponse = await getBrands(token, selectedOrganizationId);
        if (cancelled) return;

        const brandItems = brandResponse.items;
        const savedScope = loadScopeSelection();
        const nextBrandId =
          savedScope &&
          savedScope.organizationId === selectedOrganizationId &&
          savedScope.brandId &&
          brandItems.some((item) => item.id === savedScope.brandId)
            ? savedScope.brandId
            : (brandItems[0]?.id ?? '');

        setBrands(brandItems);
        setSelectedBrandId(nextBrandId);

        if (nextBrandId) {
          const [productResponse, segmentResponse] = await Promise.all([
            getProducts(token, selectedOrganizationId, nextBrandId),
            getAudienceSegments(token, selectedOrganizationId, nextBrandId),
          ]);
          if (cancelled) return;
          setProducts(productResponse.items);
          setSegments(segmentResponse.items);
        } else {
          setProducts([]);
          setSegments([]);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить scope');
          setBrands([]);
          setSelectedBrandId('');
          setProducts([]);
          setSegments([]);
          setPlans([]);
          setBriefs([]);
          setJobs([]);
          setSelectedBriefId('');
          setSelectedJobId('');
        }
      } finally {
        if (!cancelled) {
          setIsBrandsLoading(false);
        }
      }
    }

    loadScope();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedOrganizationId]);

  useEffect(() => {
    if (!selectedOrganizationId) return;
    saveScopeSelection({
      organizationId: selectedOrganizationId,
      brandId: selectedBrandId || null,
    });
  }, [selectedBrandId, selectedOrganizationId]);

  useEffect(() => {
    if (!accessToken || !selectedOrganizationId || !selectedBrandId) {
      setPlans([]);
      setBriefs([]);
      setSelectedBriefId('');
      setJobs([]);
      setSelectedJobId('');
      return;
    }

    const token = accessToken;
    let cancelled = false;

    async function loadBrandWork() {
      try {
        const [planResponse, briefResponse] = await Promise.all([
          getContentPlans(token, selectedOrganizationId, selectedBrandId, 'brand', null, null),
          getBriefs(token, selectedOrganizationId, selectedBrandId),
        ]);
        if (cancelled) return;
        const nextBriefs = briefResponse.items;
        setPlans(planResponse.items);
        setBriefs(nextBriefs);
        setSelectedBriefId((current) => {
          if (current && nextBriefs.some((brief) => brief.id === current)) return current;
          return nextBriefs[0]?.id ?? '';
        });
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить brand work');
          setPlans([]);
          setBriefs([]);
          setSelectedBriefId('');
          setJobs([]);
          setSelectedJobId('');
        }
      }
    }

    loadBrandWork();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedBrandId, selectedOrganizationId]);

  useEffect(() => {
    if (!accessToken || !selectedOrganizationId || !selectedBrandId || !selectedBriefId) {
      setJobs([]);
      setSelectedJobId('');
      return;
    }

    const token = accessToken;
    let cancelled = false;

    async function loadJobsForBrief() {
      try {
        const response = await getJobs(token, selectedOrganizationId, selectedBrandId, selectedBriefId);
        if (cancelled) return;
        const nextJobs = response.items;
        setJobs(nextJobs);
        setSelectedJobId((current) => {
          if (current && nextJobs.some((job) => job.id === current)) return current;
          return nextJobs[nextJobs.length - 1]?.id ?? '';
        });
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить jobs');
          setJobs([]);
          setSelectedJobId('');
        }
      }
    }

    loadJobsForBrief();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedBrandId, selectedBriefId, selectedOrganizationId]);

  const currentOrganization = useMemo(
    () => organizations.find((item) => item.id === selectedOrganizationId) ?? null,
    [organizations, selectedOrganizationId],
  );
  const currentBrand = useMemo(
    () => brands.find((item) => item.id === selectedBrandId) ?? null,
    [brands, selectedBrandId],
  );
  const selectedBrief = useMemo(
    () => briefs.find((item) => item.id === selectedBriefId) ?? null,
    [briefs, selectedBriefId],
  );
  const selectedJob = useMemo(
    () => jobs.find((item) => item.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  const nextAction = useMemo(() => {
    if (!selectedOrganizationId) {
      return { label: 'Выбрать organization', href: '/dashboard', reason: 'Сначала нужен рабочий organization scope.' };
    }
    if (!selectedBrandId) {
      return { label: 'Выбрать brand', href: '/brands', reason: 'Без бренда нельзя идти в производство контента.' };
    }
    if (products.length === 0) {
      return { label: 'Добавить product', href: '/products', reason: 'Для продуктового контента нужен хотя бы один product.' };
    }
    if (segments.length === 0) {
      return { label: 'Добавить audience segment', href: '/audience-segments', reason: 'Для плана и текстов нужен сегмент аудитории.' };
    }
    if (briefs.length === 0) {
      return { label: 'Создать brief', href: '/dashboard', reason: 'Следующий шаг — brief в dashboard.' };
    }
    if (plans.length === 0) {
      return { label: 'Сгенерировать content plan', href: '/content-plans', reason: 'Пора собрать рабочий контент-план.' };
    }
    if (!selectedJobId && jobs.length === 0) {
      return { label: 'Создать job', href: '/dashboard', reason: 'Теперь можно запускать генерацию через dashboard.' };
    }
    return { label: 'Открыть dashboard', href: '/dashboard', reason: 'Все базовые шаги доступны, можно смотреть детали и артефакты.' };
  }, [briefs.length, jobs.length, plans.length, products.length, segments.length, selectedBrandId, selectedJobId, selectedOrganizationId]);

  const stageCards = [
    { title: 'Organization', count: formatCount(organizations.length), detail: currentOrganization?.name ?? 'Выбор на dashboard', href: '/dashboard' },
    { title: 'Brand', count: formatCount(brands.length), detail: currentBrand?.name ?? 'Нужен активный brand scope', href: '/brands' },
    { title: 'Products', count: formatCount(products.length), detail: products[0]?.name ?? 'Добавь продукт перед генерацией', href: '/products' },
    { title: 'Audience segments', count: formatCount(segments.length), detail: segments[0]?.name ?? 'Добавь сегмент аудитории', href: '/audience-segments' },
    { title: 'Briefs', count: formatCount(briefs.length), detail: selectedBrief?.title ?? 'Создаются в dashboard', href: '/dashboard' },
    { title: 'Plans', count: formatCount(plans.length), detail: plans[0]?.title ?? 'Генерируются в content-plans', href: '/content-plans' },
    { title: 'Jobs', count: formatCount(jobs.length), detail: selectedJob ? `${selectedJob.status} · ${selectedJob.title}` : 'Показ генерации и статусов', href: '/dashboard' },
  ];

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Production flow</span>
          <h1>Единый путь от scope до готового контента</h1>
          <p className="muted">
            Этот экран собирает текущий рабочий контекст и подсказывает следующий шаг вместо того,
            чтобы заставлять тебя искать его по разным страницам.
          </p>
        </div>
        <div className="row">
          <Link className="primary-button" href={nextAction.href}>
            {nextAction.label}
          </Link>
          <Link className="secondary-button" href="/dashboard">Dashboard</Link>
          <Link className="secondary-button" href="/brands">Brands</Link>
          <Link className="secondary-button" href="/content-plans">Plans</Link>
        </div>
      </section>

      {error ? (
        <section className="card stack-sm error-card">
          <h2>Ошибка</h2>
          <p>{error}</p>
        </section>
      ) : null}

      <section className="grid two-up">
        <article className="card stack-sm">
          <div className="section-header">
            <div>
              <h2>Текущий контекст</h2>
              <p className="muted">Выбор organization и brand сохраняется локально, как и на dashboard.</p>
            </div>
          </div>

          <label className="label-stack">
            <span>Organization</span>
            <select
              className="input"
              disabled={isLoading || organizations.length === 0}
              onChange={(event) => setSelectedOrganizationId(event.target.value)}
              value={selectedOrganizationId}
            >
              {organizations.length === 0 ? <option value="">Нет доступных организаций</option> : null}
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name} · {organization.membership_role} · {organization.status}
                </option>
              ))}
            </select>
          </label>

          <label className="label-stack">
            <span>Brand</span>
            <select
              className="input"
              disabled={!selectedOrganizationId || isBrandsLoading || brands.length === 0}
              onChange={(event) => setSelectedBrandId(event.target.value)}
              value={selectedBrandId}
            >
              {isBrandsLoading ? <option value="">Загружаем бренды…</option> : null}
              {!isBrandsLoading && brands.length === 0 ? <option value="">Брендов пока нет</option> : null}
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>{brand.name}</option>
              ))}
            </select>
          </label>

          <dl className="keyvals">
            <div><dt>Products</dt><dd>{products.length}</dd></div>
            <div><dt>Segments</dt><dd>{segments.length}</dd></div>
            <div><dt>Briefs</dt><dd>{briefs.length}</dd></div>
            <div><dt>Plans</dt><dd>{plans.length}</dd></div>
            <div><dt>Jobs</dt><dd>{jobs.length}</dd></div>
          </dl>
        </article>

        <article className="card stack-sm">
          <div className="section-header">
            <div>
              <h2>Следующее действие</h2>
              <p className="muted">Кнопка справа всегда ведёт к самому полезному следующему шагу.</p>
            </div>
          </div>
          <div className="stack-sm">
            <p><strong>{nextAction.label}</strong></p>
            <p className="muted">{nextAction.reason}</p>
            <Link className="primary-button" href={nextAction.href}>Перейти</Link>
          </div>
        </article>
      </section>

      <section className="card stack-md">
        <div className="section-header">
          <div>
            <h2>Лента production flow</h2>
            <p className="muted">Тот же путь, но в одном месте и с видимым статусом каждого уровня.</p>
          </div>
        </div>

        <div className="grid two-up">
          {stageCards.map((stage) => (
            <article className="card stack-sm" key={stage.title}>
              <div className="row row-between">
                <div>
                  <h3>{stage.title}</h3>
                  <p className="muted">{stage.detail}</p>
                </div>
                <span className="pill">{formatStatus(Number(stage.count))}</span>
              </div>
              <div className="row row-between">
                <strong>{stage.count}</strong>
                <Link className="secondary-button" href={stage.href}>Open</Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="grid two-up">
        <article className="card stack-sm">
          <h2>Как идти дальше</h2>
          <ol className="checklist">
            <li>Выбери organization и brand</li>
            <li>Проверь, что есть products и audience segments</li>
            <li>Создай brief в dashboard</li>
            <li>Собери content plan</li>
            <li>Запусти job и посмотри artifact/status</li>
            <li>Прогони quality check и export при необходимости</li>
          </ol>
        </article>

        <article className="card stack-sm">
          <h2>Стартовые ссылки</h2>
          <div className="row wrap">
            <Link className="secondary-button" href="/dashboard">Dashboard</Link>
            <Link className="secondary-button" href="/brands">Brands</Link>
            <Link className="secondary-button" href="/products">Products</Link>
            <Link className="secondary-button" href="/media-assets">Media</Link>
            <Link className="secondary-button" href="/audience-segments">Audiences</Link>
            <Link className="secondary-button" href="/content-plans">Plans</Link>
          </div>
        </article>
      </section>
    </main>
  );
}
