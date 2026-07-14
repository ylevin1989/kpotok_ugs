'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { clearScopeSelection, clearSession, loadScopeSelection, loadSession, saveScopeSelection } from '../../lib/auth';
import {
  createBrief,
  generateContentPlans,
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
  if (total === 0) return 'пусто';
  if (total === 1) return 'готово';
  return 'готово';
}

function formatOrganizationRole(role?: string | null): string {
  if (!role) return '—';
  const map: Record<string, string> = {
    client_owner: 'владелец клиента',
    owner: 'владелец',
    manager: 'менеджер',
    reviewer: 'ревьюер',
    platform_admin: 'администратор платформы',
    super_admin: 'суперадминистратор',
  };
  return map[role] ?? role;
}

function formatOrganizationStatus(status?: string | null): string {
  if (!status) return '—';
  const map: Record<string, string> = {
    active: 'активна',
    inactive: 'неактивна',
    pending: 'ожидает',
  };
  return map[status] ?? status;
}

function translateWorkflowText(value?: string | null): string {
  if (!value) return '—';
  return value
    .replaceAll('Brand DNA request', 'Запрос ДНК бренда')
    .replaceAll('Generate brand DNA', 'Сгенерировать ДНК бренда')
    .replaceAll('completed', 'завершено')
    .replaceAll('ready', 'готово')
    .replaceAll('brief', 'бриф')
    .replaceAll('content plan', 'контент-план');
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
  const [briefTitle, setBriefTitle] = useState('');
  const [briefContent, setBriefContent] = useState('');
  const [planTitlePrefix, setPlanTitlePrefix] = useState('');
  const [planPlatform, setPlanPlatform] = useState('Инстаграм');
  const [planContentType, setPlanContentType] = useState('пост');
  const [planGoal, setPlanGoal] = useState('осведомлённость');
  const [planStartDate, setPlanStartDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [planEndDate, setPlanEndDate] = useState(() => new Date(Date.now() + 6 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [isLoading, setIsLoading] = useState(true);
  const [isBrandsLoading, setIsBrandsLoading] = useState(false);
  const [isScopeLoading, setIsScopeLoading] = useState(false);
  const [isCreatingBrief, setIsCreatingBrief] = useState(false);
  const [isGeneratingPlans, setIsGeneratingPlans] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
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
          setError(err instanceof Error ? err.message : 'Не удалось загрузить область');
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
          setError(err instanceof Error ? err.message : 'Не удалось загрузить данные бренда');
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

  useEffect(() => {
    if (!currentBrand) return;
    setBriefTitle((current) => (current.trim() ? current : `${currentBrand.name} — бриф`));
    setBriefContent((current) =>
      current.trim()
        ? current
        : `Бренд: ${currentBrand.name}\nОрганизация: ${currentOrganization?.name ?? ''}\nЦель: краткий рабочий бриф для контент-плана.`,
    );
    setPlanTitlePrefix((current) => (current.trim() ? current : currentBrand.name));
  }, [currentBrand, currentOrganization?.name]);

  const nextAction = useMemo(() => {
    if (!selectedOrganizationId) {
      return { label: 'Выбрать организацию', href: '/dashboard', reason: 'Сначала нужна рабочая область организации.' };
    }
    if (!selectedBrandId) {
      return { label: 'Выбрать бренд', href: '/brands', reason: 'Без бренда нельзя идти в производство контента.' };
    }
    if (products.length === 0) {
      return { label: 'Добавить продукт', href: '/products', reason: 'Для продуктового контента нужен хотя бы один продукт.' };
    }
    if (segments.length === 0) {
      return { label: 'Добавить сегмент аудитории', href: '/audience-segments', reason: 'Для плана и текстов нужен сегмент аудитории.' };
    }
    if (briefs.length === 0) {
      return { label: 'Создать бриф здесь', href: '#quick-actions', reason: 'Сначала собери бриф, не уходя с этой страницы.' };
    }
    if (plans.length === 0) {
      return { label: 'Сгенерировать планы здесь', href: '#quick-actions', reason: 'После брифа можно сразу собрать контент-план.' };
    }
    if (!selectedJobId && jobs.length === 0) {
      return { label: 'Создать задачу', href: '/dashboard', reason: 'Теперь можно запускать генерацию через панель.' };
    }
    return { label: 'Открыть панель', href: '/dashboard', reason: 'Все базовые шаги доступны, можно смотреть детали и артефакты.' };
  }, [briefs.length, jobs.length, plans.length, products.length, segments.length, selectedBrandId, selectedJobId, selectedOrganizationId]);

  const stageCards = [
    { title: 'Организация', count: formatCount(organizations.length), detail: currentOrganization?.name ?? 'Выбор на панели', href: '/dashboard' },
    { title: 'Бренд', count: formatCount(brands.length), detail: currentBrand?.name ?? 'Нужна активная область бренда', href: '/brands' },
    { title: 'Продукты', count: formatCount(products.length), detail: products[0]?.name ?? 'Добавь продукт перед генерацией', href: '/products' },
    { title: 'Сегменты аудитории', count: formatCount(segments.length), detail: segments[0]?.name ?? 'Добавь сегмент аудитории', href: '/audience-segments' },
    { title: 'Брифы', count: formatCount(briefs.length), detail: selectedBrief?.title ? translateWorkflowText(selectedBrief.title) : 'Создаются на панели', href: '/dashboard' },
    { title: 'Планы', count: formatCount(plans.length), detail: plans[0]?.title ?? 'Генерируются в разделе контент-планов', href: '/content-plans' },
    { title: 'Задачи', count: formatCount(jobs.length), detail: selectedJob ? `${translateWorkflowText(selectedJob.status)} · ${translateWorkflowText(selectedJob.title)}` : 'Показ генерации и статусов', href: '/dashboard' },
  ];

  async function handleCreateBrief(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionMessage(null);

    if (!accessToken || !selectedOrganizationId || !selectedBrandId) {
      setActionMessage('Сначала выбери организацию и бренд.');
      return;
    }

    const title = briefTitle.trim();
    const content = briefContent.trim();
    if (!title || !content) {
      setActionMessage('Для брифа нужны и заголовок, и содержание.');
      return;
    }

    setIsCreatingBrief(true);
    try {
      const created = await createBrief(accessToken, {
        organization_id: selectedOrganizationId,
        brand_id: selectedBrandId,
        title,
        content,
      });
      setBriefs((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setSelectedBriefId(created.id);
      setActionMessage(`Бриф создан: ${created.title}`);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Не удалось создать бриф');
    } finally {
      setIsCreatingBrief(false);
    }
  }

  async function handleGeneratePlans(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionMessage(null);

    if (!accessToken || !selectedOrganizationId || !selectedBrandId) {
      setActionMessage('Сначала выбери организацию и бренд.');
      return;
    }

    setIsGeneratingPlans(true);
    try {
      const generated = await generateContentPlans(accessToken, {
        organization_id: selectedOrganizationId,
        brand_id: selectedBrandId,
        product_id: products[0]?.id ?? null,
        audience_segment_id: segments[0]?.id ?? null,
        scope: 'brand',
        start_date: planStartDate,
        end_date: planEndDate,
        title_prefix: planTitlePrefix.trim() || undefined,
        platform: planPlatform.trim(),
        content_type: planContentType.trim(),
        goal: planGoal.trim(),
        status: 'draft',
      });
      setPlans(generated.items);
      setActionMessage(`Контент-планы сгенерированы: ${generated.items.length}`);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Не удалось сгенерировать content plans');
    } finally {
      setIsGeneratingPlans(false);
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">ПОТОК ПРОИЗВОДСТВА</span>
          <h1>Единый путь от области до готового контента</h1>
          <p className="muted">
            Этот экран собирает текущий рабочий контекст и подсказывает следующий шаг вместо того,
            чтобы заставлять тебя искать его по разным страницам.
          </p>
        </div>
        <div className="row">
          <Link className="primary-button" href={nextAction.href}>
            {nextAction.label}
          </Link>
          <Link className="secondary-button" href="/dashboard">Панель</Link>
          <Link className="secondary-button" href="/brands">Бренды</Link>
          <Link className="secondary-button" href="/content-plans">Планы</Link>
        </div>
      </section>

      <section id="quick-actions" className="grid two-up">
        <article className="card stack-sm">
          <div className="section-header">
            <div>
              <h2>Быстрый бриф</h2>
              <p className="muted">Создай бриф прямо отсюда, не прыгая по экрану.</p>
            </div>
          </div>
          <form className="stack-sm" onSubmit={handleCreateBrief}>
            <label className="label-stack">
              <span>Название брифа</span>
              <input
                className="input"
                onChange={(event) => setBriefTitle(event.target.value)}
                placeholder="Например, еженедельный бриф бренда"
                value={briefTitle}
              />
            </label>
            <label className="label-stack">
              <span>Содержание брифа</span>
              <textarea
                className="input"
                onChange={(event) => setBriefContent(event.target.value)}
                rows={6}
                value={briefContent}
              />
            </label>
            <button className="primary-button" disabled={isCreatingBrief} type="submit">
              {isCreatingBrief ? 'Создаём…' : 'Создать бриф'}
            </button>
          </form>
        </article>

        <article className="card stack-sm">
          <div className="section-header">
            <div>
              <h2>Быстрый контент-план</h2>
              <p className="muted">Собери план из текущей области бренда и первого доступного контекста.</p>
            </div>
          </div>
          <form className="stack-sm" onSubmit={handleGeneratePlans}>
            <label className="label-stack">
              <span>Префикс названия</span>
              <input
                className="input"
                onChange={(event) => setPlanTitlePrefix(event.target.value)}
                placeholder="Например, Лаконика"
                value={planTitlePrefix}
              />
            </label>
            <div className="grid two-up">
              <label className="label-stack">
                <span>Платформа</span>
                <input className="input" onChange={(event) => setPlanPlatform(event.target.value)} value={planPlatform} />
              </label>
              <label className="label-stack">
                <span>Тип контента</span>
                <input className="input" onChange={(event) => setPlanContentType(event.target.value)} value={planContentType} />
              </label>
            </div>
            <label className="label-stack">
              <span>Цель</span>
              <input className="input" onChange={(event) => setPlanGoal(event.target.value)} value={planGoal} />
            </label>
            <div className="grid two-up">
              <label className="label-stack">
                <span>Дата начала</span>
                <input className="input" type="date" onChange={(event) => setPlanStartDate(event.target.value)} value={planStartDate} />
              </label>
              <label className="label-stack">
                <span>Дата окончания</span>
                <input className="input" type="date" onChange={(event) => setPlanEndDate(event.target.value)} value={planEndDate} />
              </label>
            </div>
            <button className="primary-button" disabled={isGeneratingPlans} type="submit">
              {isGeneratingPlans ? 'Генерируем…' : 'Сгенерировать планы'}
            </button>
          </form>
        </article>
      </section>

      {actionMessage ? (
        <section className="card stack-sm">
          <h2>Быстрое действие</h2>
          <p>{actionMessage}</p>
        </section>
      ) : null}

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
              <p className="muted">Выбор организации и бренда сохраняется локально, как и на панели.</p>
            </div>
          </div>

          <label className="label-stack">
            <span>Организация</span>
            <select
              className="input"
              disabled={isLoading || organizations.length === 0}
              onChange={(event) => setSelectedOrganizationId(event.target.value)}
              value={selectedOrganizationId}
            >
              {organizations.length === 0 ? <option value="">Нет доступных организаций</option> : null}
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name} · {formatOrganizationRole(organization.membership_role)} · {formatOrganizationStatus(organization.status)}
                </option>
              ))}
            </select>
          </label>

          <label className="label-stack">
            <span>Бренд</span>
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
            <div><dt>Продукты</dt><dd>{products.length}</dd></div>
            <div><dt>Сегменты</dt><dd>{segments.length}</dd></div>
            <div><dt>Брифы</dt><dd>{briefs.length}</dd></div>
            <div><dt>Планы</dt><dd>{plans.length}</dd></div>
            <div><dt>Задачи</dt><dd>{jobs.length}</dd></div>
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
            <h2>Лента потока производства</h2>
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
                <Link className="secondary-button" href={stage.href}>Открыть</Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="grid two-up">
        <article className="card stack-sm">
          <h2>Как двигаться дальше</h2>
          <ol className="checklist">
            <li>Выбери организацию и бренд</li>
            <li>Проверь, что есть продукты и сегменты аудитории</li>
            <li>Создай бриф в панели</li>
            <li>Собери контент-план</li>
            <li>Запусти задачу и посмотри артефакт/статус</li>
            <li>Прогони проверку качества и экспорт при необходимости</li>
          </ol>
        </article>

        <article className="card stack-sm">
          <h2>Быстрые переходы</h2>
          <div className="row wrap">
            <Link className="secondary-button" href="/dashboard">Панель</Link>
            <Link className="secondary-button" href="/brands">Бренды</Link>
            <Link className="secondary-button" href="/products">Продукты</Link>
            <Link className="secondary-button" href="/media-assets">Медиа</Link>
            <Link className="secondary-button" href="/audience-segments">Аудитории</Link>
            <Link className="secondary-button" href="/content-plans">Планы</Link>
          </div>
        </article>
      </section>
    </main>
  );
}
