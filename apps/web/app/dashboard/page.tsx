'use client';

import type { FormEvent } from 'react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  clearScopeSelection,
  clearSession,
  loadScopeSelection,
  loadSession,
  saveScopeSelection,
} from '../../lib/auth';
import {
  createBrief,
  createJob,
  downloadJobArtifact,
  getBrands,
  getBriefs,
  getJob,
  getJobArtifactText,
  getJobs,
  getMe,
  getOrganizations,
} from '../../lib/api';
import type { BrandRead, BriefRead, JobRead, MeResponse, OrganizationRead } from '../../lib/types';

function formatDateTime(value: string | null): string {
  if (!value) {
    return '—';
  }
  return new Date(value).toLocaleString('ru-RU');
}

function formatExecutionProfile(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function summarizeJob(job: JobRead): string {
  const progress = job.execution_trace?.last_progress?.progress_percent;
  const stage = job.execution_trace?.last_progress?.stage_label || job.last_stage || '—';
  if (typeof progress === 'number') {
    return `${job.status} · ${progress}% · ${stage}`;
  }
  return `${job.status} · ${stage}`;
}

function canPreviewArtifact(contentType: string | null): boolean {
  if (!contentType) {
    return true;
  }
  return contentType.startsWith('text/') || contentType.includes('json') || contentType.includes('xml');
}

function buildArtifactFilename(job: JobRead): string {
  const extension = job.output_artifact_content_type?.includes('json') ? 'json' : 'txt';
  return `job-${job.id}-artifact.${extension}`;
}

const EXECUTION_PROFILE_REFERENCE = [
  { key: 'general_content', label: 'General Content', roles: ['Mike', 'Emma', 'Iris', 'Alex', 'David'] },
  { key: 'seo_content', label: 'SEO Content', roles: ['Mike', 'Emma', 'Iris', 'Sarah', 'Alex', 'David'] },
  { key: 'ads_content', label: 'Ads Content', roles: ['Mike', 'Emma', 'Iris', 'Adrian', 'Alex', 'David'] },
  { key: 'architecture_support', label: 'Architecture Support', roles: ['Mike', 'Bob', 'David'] },
] as const;

export default function DashboardPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [data, setData] = useState<MeResponse | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [briefs, setBriefs] = useState<BriefRead[]>([]);
  const [jobs, setJobs] = useState<JobRead[]>([]);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState('');
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedBriefId, setSelectedBriefId] = useState('');
  const [selectedJobId, setSelectedJobId] = useState('');
  const [briefTitle, setBriefTitle] = useState('');
  const [briefContent, setBriefContent] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [selectedExecutionProfile, setSelectedExecutionProfile] = useState('general_content');
  const [artifactText, setArtifactText] = useState<string | null>(null);
  const [artifactContentType, setArtifactContentType] = useState<string | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBrandsLoading, setIsBrandsLoading] = useState(false);
  const [isBriefsLoading, setIsBriefsLoading] = useState(false);
  const [isJobsLoading, setIsJobsLoading] = useState(false);
  const [isJobDetailLoading, setIsJobDetailLoading] = useState(false);
  const [isArtifactLoading, setIsArtifactLoading] = useState(false);
  const [isArtifactDownloading, setIsArtifactDownloading] = useState(false);
  const [isCreatingBrief, setIsCreatingBrief] = useState(false);
  const [isCreatingJob, setIsCreatingJob] = useState(false);

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
        if (cancelled) {
          return;
        }

        const orgItems = orgResponse.items;
        const savedScope = loadScopeSelection();
        const nextOrganizationId =
          savedScope && orgItems.some((item) => item.id === savedScope.organizationId)
            ? savedScope.organizationId
            : (orgItems[0]?.id ?? '');

        setData(me);
        setOrganizations(orgItems);
        setSelectedOrganizationId(nextOrganizationId);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Не удалось загрузить профиль';
          setError(message);
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
      setBriefs([]);
      setSelectedBriefId('');
      setJobs([]);
      setSelectedJobId('');
      return;
    }

    const token = accessToken;
    let cancelled = false;
    setIsBrandsLoading(true);

    async function loadBrands() {
      try {
        const response = await getBrands(token, selectedOrganizationId);
        if (cancelled) {
          return;
        }

        const brandItems = response.items;
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
        setBriefError(null);
        setJobError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить бренды');
          setBrands([]);
          setSelectedBrandId('');
          setBriefs([]);
          setSelectedBriefId('');
          setJobs([]);
          setSelectedJobId('');
        }
      } finally {
        if (!cancelled) {
          setIsBrandsLoading(false);
        }
      }
    }

    loadBrands();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedOrganizationId]);

  useEffect(() => {
    if (!selectedOrganizationId) {
      return;
    }

    saveScopeSelection({
      organizationId: selectedOrganizationId,
      brandId: selectedBrandId || null,
    });
  }, [selectedBrandId, selectedOrganizationId]);

  useEffect(() => {
    if (!accessToken || !selectedOrganizationId || !selectedBrandId) {
      setBriefs([]);
      setSelectedBriefId('');
      setJobs([]);
      setSelectedJobId('');
      return;
    }

    const token = accessToken;
    let cancelled = false;
    setIsBriefsLoading(true);

    async function loadBriefs() {
      try {
        const response = await getBriefs(token, selectedOrganizationId, selectedBrandId);
        if (cancelled) {
          return;
        }
        const nextBriefs = response.items;
        setBriefs(nextBriefs);
        setSelectedBriefId((current) => {
          if (current && nextBriefs.some((brief) => brief.id === current)) {
            return current;
          }
          return nextBriefs[0]?.id ?? '';
        });
        setBriefError(null);
      } catch (err) {
        if (!cancelled) {
          setBriefError(err instanceof Error ? err.message : 'Не удалось загрузить briefs');
          setBriefs([]);
          setSelectedBriefId('');
        }
      } finally {
        if (!cancelled) {
          setIsBriefsLoading(false);
        }
      }
    }

    loadBriefs();

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
    setIsJobsLoading(true);

    async function loadJobs() {
      try {
        const response = await getJobs(token, selectedOrganizationId, selectedBrandId, selectedBriefId);
        if (cancelled) {
          return;
        }
        const nextJobs = response.items;
        setJobs(nextJobs);
        setSelectedJobId((current) => {
          if (current && nextJobs.some((job) => job.id === current)) {
            return current;
          }
          return nextJobs[nextJobs.length - 1]?.id ?? '';
        });
        setJobError(null);
      } catch (err) {
        if (!cancelled) {
          setJobError(err instanceof Error ? err.message : 'Не удалось загрузить jobs');
          setJobs([]);
          setSelectedJobId('');
        }
      } finally {
        if (!cancelled) {
          setIsJobsLoading(false);
        }
      }
    }

    loadJobs();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedBrandId, selectedBriefId, selectedOrganizationId]);

  useEffect(() => {
    if (!accessToken || !selectedJobId) {
      return;
    }

    const token = accessToken;
    let cancelled = false;
    setIsJobDetailLoading(true);

    async function refreshSelectedJob() {
      try {
        const job = await getJob(token, selectedJobId);
        if (cancelled) {
          return;
        }
        setJobs((current) => current.map((item) => (item.id === job.id ? job : item)));
        setJobError(null);
      } catch (err) {
        if (!cancelled) {
          setJobError(err instanceof Error ? err.message : 'Не удалось загрузить job detail');
        }
      } finally {
        if (!cancelled) {
          setIsJobDetailLoading(false);
        }
      }
    }

    refreshSelectedJob();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedJobId]);

  const memberships = useMemo(() => data?.memberships ?? [], [data]);
  const selectedOrganization = useMemo(
    () => organizations.find((organization) => organization.id === selectedOrganizationId) ?? null,
    [organizations, selectedOrganizationId],
  );
  const selectedBrand = useMemo(
    () => brands.find((brand) => brand.id === selectedBrandId) ?? null,
    [brands, selectedBrandId],
  );
  const selectedBrief = useMemo(
    () => briefs.find((brief) => brief.id === selectedBriefId) ?? null,
    [briefs, selectedBriefId],
  );
  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );
  const canManageSelectedOrganization =
    selectedOrganization?.membership_role === 'client_owner' ||
    selectedOrganization?.membership_role === 'client_manager';
  const isSelectedScopeReviewer = selectedOrganization?.membership_role === 'client_reviewer';

  useEffect(() => {
    if (!selectedJob) {
      setArtifactText(null);
      setArtifactContentType(null);
      setArtifactError(null);
      setIsArtifactLoading(false);
      return;
    }

    if (!selectedJob.output_artifact_key) {
      setArtifactText(null);
      setArtifactContentType(null);
      setArtifactError(null);
      setIsArtifactLoading(false);
      return;
    }

    if (!accessToken || !canPreviewArtifact(selectedJob.output_artifact_content_type)) {
      setArtifactText(null);
      setArtifactContentType(selectedJob.output_artifact_content_type ?? null);
      setArtifactError(null);
      setIsArtifactLoading(false);
      return;
    }

    let cancelled = false;
    const token = accessToken;
    const job = selectedJob;
    setIsArtifactLoading(true);
    setArtifactError(null);
    setArtifactContentType(job.output_artifact_content_type ?? null);

    async function loadArtifactPreview() {
      try {
        const artifact = await getJobArtifactText(token, job.id);
        if (cancelled) {
          return;
        }
        setArtifactText(artifact.content);
        setArtifactContentType(artifact.contentType);
      } catch (err) {
        if (!cancelled) {
          setArtifactText(null);
          setArtifactError(err instanceof Error ? err.message : 'Не удалось загрузить artifact');
        }
      } finally {
        if (!cancelled) {
          setIsArtifactLoading(false);
        }
      }
    }

    loadArtifactPreview();

    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedJob]);

  async function handleDownloadArtifact() {
    if (!accessToken || !selectedJob || !selectedJob.output_artifact_key) {
      return;
    }

    const token = accessToken;
    const job = selectedJob;
    setIsArtifactDownloading(true);
    setArtifactError(null);
    try {
      const artifact = await downloadJobArtifact(token, job.id);
      const url = window.URL.createObjectURL(artifact.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = buildArtifactFilename(job);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setArtifactContentType(artifact.contentType);
    } catch (err) {
      setArtifactError(err instanceof Error ? err.message : 'Не удалось скачать artifact');
    } finally {
      setIsArtifactDownloading(false);
    }
  }

  async function handleCreateBrief(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !selectedOrganizationId || !selectedBrandId) {
      setBriefError('Сначала выбери organization и brand');
      return;
    }

    setIsCreatingBrief(true);
    setBriefError(null);
    try {
      const created = await createBrief(accessToken, {
        organization_id: selectedOrganizationId,
        brand_id: selectedBrandId,
        title: briefTitle.trim(),
        content: briefContent.trim(),
      });
      setBriefs((current) => [...current, created]);
      setSelectedBriefId(created.id);
      setBriefTitle('');
      setBriefContent('');
    } catch (err) {
      setBriefError(err instanceof Error ? err.message : 'Не удалось создать brief');
    } finally {
      setIsCreatingBrief(false);
    }
  }

  async function handleCreateJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !selectedOrganizationId || !selectedBrandId || !selectedBriefId) {
      setJobError('Сначала выбери brief');
      return;
    }

    setIsCreatingJob(true);
    setJobError(null);
    try {
      const created = await createJob(accessToken, {
        organization_id: selectedOrganizationId,
        brand_id: selectedBrandId,
        brief_id: selectedBriefId,
        title: jobTitle.trim(),
        execution_profile: selectedExecutionProfile,
      });
      setJobs((current) => [...current, created]);
      setSelectedJobId(created.id);
      setJobTitle('');
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'Не удалось создать job');
    } finally {
      setIsCreatingJob(false);
    }
  }

  function handleLogout() {
    clearScopeSelection();
    clearSession();
    router.replace('/login');
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Dashboard</span>
          <h1>Content Factory MVP shell</h1>
          <p className="muted">
            Это уже не stub: web слой авторизуется против live API, показывает доступные
            организации и даёт выбрать текущий рабочий scope для следующих экранов.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/brands">
            Brands
          </Link>
          <Link className="secondary-button" href="/products">
            Products
          </Link>
          <Link className="secondary-button" href="/media-assets">
            Media
          </Link>
          <Link className="secondary-button" href="/audience-segments">
            Audiences
          </Link>
          <Link className="secondary-button" href="/content-plans">
            Plans
          </Link>
          <Link className="secondary-button" href="/subscriptions">
            Subscriptions
          </Link>
          <button className="secondary-button" onClick={handleLogout} type="button">
            Выйти
          </button>
        </div>
      </section>

      {isLoading ? (
        <section className="card stack-sm">
          <h2>Загружаем профиль</h2>
          <p className="muted">Проверяем токен, организации и список членств через live API.</p>
        </section>
      ) : null}

      {error ? (
        <section className="card stack-sm error-card">
          <h2>Сессия сброшена</h2>
          <p>{error}</p>
        </section>
      ) : null}

      {data ? (
        <>
          <section className="grid two-up">
            <article className="card stack-sm">
              <h2>Пользователь</h2>
              <dl className="keyvals">
                <div><dt>Email</dt><dd>{data.user.email}</dd></div>
                <div><dt>Имя</dt><dd>{data.user.full_name ?? '—'}</dd></div>
                <div><dt>Platform role</dt><dd>{data.user.platform_role ?? '—'}</dd></div>
                <div><dt>Active</dt><dd>{data.user.is_active ? 'yes' : 'no'}</dd></div>
              </dl>
            </article>

            <article className="card stack-sm">
              <h2>Статус MVP</h2>
              <ul className="checklist">
                <li>Auth shell подключён к live API</li>
                <li>Организации подтягиваются из `/api/v1/organizations`</li>
                <li>Бренды подтягиваются из `/api/v1/brands?organization_id=...`</li>
                <li>Briefs уже можно создавать и читать в выбранном scope</li>
                <li>Jobs уже можно ставить в очередь и читать их status/detail</li>
                <li>Result text и artifact surface теперь доступны прямо в dashboard</li>
              </ul>
            </article>
          </section>

          <section className="grid two-up">
            <article className="card stack-md">
              <div className="section-header">
                <div>
                  <h2>Текущий рабочий scope</h2>
                  <p className="muted">Локально запоминаем выбранные organization и brand для briefs и будущих job screens.</p>
                </div>
              </div>

              <label className="label-stack">
                <span>Organization</span>
                <select className="input" onChange={(event) => setSelectedOrganizationId(event.target.value)} value={selectedOrganizationId}>
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
                <select className="input" disabled={!selectedOrganizationId || isBrandsLoading || brands.length === 0} onChange={(event) => setSelectedBrandId(event.target.value)} value={selectedBrandId}>
                  {isBrandsLoading ? <option value="">Загружаем бренды…</option> : null}
                  {!isBrandsLoading && brands.length === 0 ? <option value="">Брендов пока нет</option> : null}
                  {brands.map((brand) => (
                    <option key={brand.id} value={brand.id}>{brand.name}</option>
                  ))}
                </select>
              </label>
            </article>

            <article className="card stack-sm">
              <h2>Выбранный контекст</h2>
              <dl className="keyvals">
                <div><dt>Organization</dt><dd>{selectedOrganization ? `${selectedOrganization.name} (${selectedOrganization.slug})` : '—'}</dd></div>
                <div><dt>Organization role</dt><dd>{selectedOrganization?.membership_role ?? '—'}</dd></div>
                <div><dt>Access mode</dt><dd>{canManageSelectedOrganization ? 'manager/owner write access' : 'reviewer read-only'}</dd></div>
                <div><dt>Brand</dt><dd>{selectedBrand ? `${selectedBrand.name} (${selectedBrand.slug})` : '—'}</dd></div>
                <div><dt>Brand count in scope</dt><dd>{brands.length}</dd></div>
              </dl>

              {isSelectedScopeReviewer ? (
                <p className="muted">Этот scope для reviewer работает в режиме только чтения. Создавать briefs и jobs здесь могут только manager/owner.</p>
              ) : null}
            </article>
          </section>

          <section className="grid two-up briefs-grid">
            <article className="card stack-md">
              <div className="section-header">
                <div>
                  <h2>Создать brief</h2>
                  <p className="muted">Первый продуктовый happy path: записать brief в выбранный brand scope.</p>
                </div>
              </div>

              {canManageSelectedOrganization ? (
                <form className="stack-md" onSubmit={handleCreateBrief}>
                  <label className="label-stack">
                    <span>Title</span>
                    <input className="input" maxLength={200} onChange={(event) => setBriefTitle(event.target.value)} placeholder="Например: Q3 launch brief" required value={briefTitle} />
                  </label>

                  <label className="label-stack">
                    <span>Content</span>
                    <textarea className="input textarea" onChange={(event) => setBriefContent(event.target.value)} placeholder="Цель, аудитория, каналы, ограничения, tone of voice..." required rows={8} value={briefContent} />
                  </label>

                  {briefError ? <p className="error-text">{briefError}</p> : null}

                  <button className="primary-button" disabled={isCreatingBrief || !selectedOrganizationId || !selectedBrandId || !briefTitle.trim() || !briefContent.trim()} type="submit">
                    {isCreatingBrief ? 'Создаём brief…' : 'Создать brief'}
                  </button>
                </form>
              ) : (
                <div className="card stack-sm">
                  <p className="muted">У reviewer нет права создавать brief в этом scope.</p>
                  <p className="muted">Можно читать briefs, выбирать активный brief и смотреть jobs/result/artifacts, но запись доступна только manager/owner.</p>
                </div>
              )}
            </article>

            <article className="card stack-md">
              <div className="section-header">
                <div>
                  <h2>Briefs в текущем scope</h2>
                  <p className="muted">Читаем live список из `/api/v1/briefs` для выбранных organization/brand.</p>
                </div>
                <span className="pill">{briefs.length}</span>
              </div>

              <label className="label-stack">
                <span>Активный brief для jobs</span>
                <select className="input" disabled={briefs.length === 0 || isBriefsLoading} onChange={(event) => setSelectedBriefId(event.target.value)} value={selectedBriefId}>
                  {isBriefsLoading ? <option value="">Загружаем briefs…</option> : null}
                  {!isBriefsLoading && briefs.length === 0 ? <option value="">В этом scope пока нет briefs</option> : null}
                  {briefs.map((brief) => (
                    <option key={brief.id} value={brief.id}>{brief.title}</option>
                  ))}
                </select>
              </label>

              {!isBriefsLoading && briefs.length === 0 ? (
                <p className="muted">В этом scope пока нет briefs. Создай первый слева.</p>
              ) : null}

              <div className="stack-sm">
                {briefs.map((brief) => (
                  <article className="brief-card stack-xs" key={brief.id}>
                    <div className="brief-meta">
                      <strong>{brief.title}</strong>
                      <span className="pill subtle-pill">{new Date(brief.created_at).toLocaleString('ru-RU')}</span>
                    </div>
                    <p className="brief-content">{brief.content}</p>
                    <div className="row-label mono">{brief.id}</div>
                  </article>
                ))}
              </div>
            </article>
          </section>

          <section className="grid two-up briefs-grid">
            <article className="card stack-md">
              <div className="section-header">
                <div>
                  <h2>Создать job</h2>
                  <p className="muted">Постановка job в очередь по выбранному brief. Следующий шаг после MVP-04.</p>
                </div>
              </div>

              {canManageSelectedOrganization ? (
                <form className="stack-md" onSubmit={handleCreateJob}>
                  <label className="label-stack">
                    <span>Brief</span>
                    <select className="input" disabled={briefs.length === 0 || isBriefsLoading} onChange={(event) => setSelectedBriefId(event.target.value)} value={selectedBriefId}>
                      {briefs.length === 0 ? <option value="">Сначала создай или выбери brief</option> : null}
                      {briefs.map((brief) => (
                        <option key={brief.id} value={brief.id}>{brief.title}</option>
                      ))}
                    </select>
                  </label>

                  <label className="label-stack">
                    <span>Job title</span>
                    <input className="input" maxLength={200} onChange={(event) => setJobTitle(event.target.value)} placeholder="Например: Generate launch assets" required value={jobTitle} />
                  </label>

                  <label className="label-stack">
                    <span>Execution profile</span>
                    <select className="input" onChange={(event) => setSelectedExecutionProfile(event.target.value)} value={selectedExecutionProfile}>
                      {EXECUTION_PROFILE_REFERENCE.map((profile) => (
                        <option key={profile.key} value={profile.key}>
                          {profile.label} · {profile.key}
                        </option>
                      ))}
                    </select>
                  </label>

                  {selectedBrief ? (
                    <div className="card stack-xs">
                      <div className="row-label">Выбранный brief</div>
                      <strong>{selectedBrief.title}</strong>
                      <p className="muted">{selectedBrief.content}</p>
                    </div>
                  ) : null}

                  {jobError ? <p className="error-text">{jobError}</p> : null}

                  <button className="primary-button" disabled={isCreatingJob || !selectedOrganizationId || !selectedBrandId || !selectedBriefId || !jobTitle.trim()} type="submit">
                    {isCreatingJob ? 'Ставим job в очередь…' : 'Создать job'}
                  </button>
                </form>
              ) : (
                <div className="card stack-sm">
                  <p className="muted">У reviewer нет права ставить job в очередь в этом scope.</p>
                  <p className="muted">Можно выбирать brief, читать список jobs и открывать detail/result/artifact, но запись доступна только manager/owner.</p>
                </div>
              )}
            </article>

            <article className="card stack-md">
              <div className="section-header">
                <div>
                  <h2>Jobs по выбранному brief</h2>
                  <p className="muted">Читаем live список из `/api/v1/jobs` и сразу подтягиваем detail выбранной job.</p>
                </div>
                <span className="pill">{jobs.length}</span>
              </div>

              {isJobsLoading ? <p className="muted">Загружаем jobs…</p> : null}
              {!isJobsLoading && jobs.length === 0 ? <p className="muted">Для этого brief пока нет jobs.</p> : null}

              <div className="stack-sm">
                {jobs.map((job) => (
                  <button
                    className="secondary-button"
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    type="button"
                  >
                    {job.title} · {summarizeJob(job)}
                  </button>
                ))}
              </div>
            </article>
          </section>

          <section className="card stack-md">
            <div className="section-header">
              <div>
                <h2>Job detail / status</h2>
                <p className="muted">Выбранная job подтягивается через `/api/v1/jobs/{'{job_id}'}`.</p>
              </div>
              {selectedJob ? <span className="pill">{selectedJob.status}</span> : null}
            </div>

            {isJobDetailLoading ? <p className="muted">Обновляем detail job…</p> : null}
            {!selectedJob ? <p className="muted">Выбери job из списка выше.</p> : null}

            {selectedJob ? (
              <div className="grid two-up">
                <article className="card stack-sm">
                  <h3>Основное</h3>
                  <dl className="keyvals">
                    <div><dt>Title</dt><dd>{selectedJob.title}</dd></div>
                    <div><dt>Status</dt><dd>{selectedJob.status}</dd></div>
                    <div><dt>Attempt count</dt><dd>{selectedJob.attempt_count}</dd></div>
                    <div><dt>Last stage</dt><dd>{selectedJob.last_stage ?? '—'}</dd></div>
                    <div><dt>Worker</dt><dd>{selectedJob.worker_id ?? '—'}</dd></div>
                    <div><dt>Started</dt><dd>{formatDateTime(selectedJob.started_at)}</dd></div>
                    <div><dt>Finished</dt><dd>{formatDateTime(selectedJob.finished_at)}</dd></div>
                    <div><dt>Heartbeat</dt><dd>{formatDateTime(selectedJob.last_heartbeat_at)}</dd></div>
                  </dl>
                </article>

                <article className="card stack-sm">
                  <h3>Progress / output</h3>
                  <dl className="keyvals">
                    <div><dt>Progress</dt><dd>{selectedJob.execution_trace?.last_progress?.progress_percent ?? '—'}</dd></div>
                    <div><dt>Stage label</dt><dd>{selectedJob.execution_trace?.last_progress?.stage_label ?? '—'}</dd></div>
                    <div><dt>Progress message</dt><dd>{selectedJob.execution_trace?.last_progress?.progress_message ?? '—'}</dd></div>
                    <div><dt>Final status</dt><dd>{selectedJob.execution_trace?.final_status ?? '—'}</dd></div>
                    <div><dt>Failure reason</dt><dd>{selectedJob.execution_trace?.failure_reason ?? selectedJob.error_message ?? '—'}</dd></div>
                  </dl>

                  <div className="stack-sm">
                    <div className="section-header compact-header">
                      <div>
                        <h3>Execution profile reference</h3>
                        <p className="muted">Канонический справочник поддерживаемых execution profiles и ordered role chains из `docs/internal-execution-api-bundle.md`.</p>
                      </div>
                      <span className="pill subtle-pill">{EXECUTION_PROFILE_REFERENCE.length}</span>
                    </div>

                    <div className="stack-sm">
                      {EXECUTION_PROFILE_REFERENCE.map((profile) => (
                        <article className="brief-card stack-xs" key={profile.key}>
                          <div className="brief-meta">
                            <strong>{profile.label}</strong>
                            <span className="pill subtle-pill mono">{profile.key}</span>
                          </div>
                          <p className="muted">{profile.roles.join(' → ')}</p>
                        </article>
                      ))}
                    </div>
                  </div>

                  <div className="stack-sm">
                    <div className="section-header compact-header">
                      <div>
                        <h3>Internal execution plan</h3>
                        <p className="muted">Показываем resolved internal roles, которые API уже вернул для этой job.</p>
                      </div>
                      <span className="pill subtle-pill">{selectedJob.internal_role_plan.length}</span>
                    </div>

                    <dl className="keyvals">
                      <div><dt>Execution profile</dt><dd>{formatExecutionProfile(selectedJob.execution_profile)}</dd></div>
                      <div><dt>Profile key</dt><dd className="mono">{selectedJob.execution_profile}</dd></div>
                    </dl>

                    {selectedJob.internal_role_plan.length > 0 ? (
                      <div className="stack-sm">
                        {selectedJob.internal_role_plan.map((role, index) => (
                          <article className="brief-card stack-xs" key={`${selectedJob.id}-${role.role_id}`}>
                            <div className="brief-meta">
                              <strong>{index + 1}. {role.label}</strong>
                              <span className="pill subtle-pill mono">{role.role_id}</span>
                            </div>
                            <p className="muted">{role.purpose}</p>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="muted">У этой job пока нет internal role plan.</p>
                    )}
                  </div>

                  <div className="stack-sm">
                    <div className="section-header compact-header">
                      <div>
                        <h3>Compact trace summary</h3>
                        <p className="muted">Сводка `execution_trace.trace_compact_summary` для быстрого operator readback.</p>
                      </div>
                    </div>

                    {selectedJob.execution_trace?.trace_compact_summary ? (
                      <dl className="keyvals">
                        <div><dt>Current stage</dt><dd>{selectedJob.execution_trace.trace_compact_summary.current_stage ?? '—'}</dd></div>
                        <div><dt>Final status</dt><dd>{selectedJob.execution_trace.trace_compact_summary.final_status ?? '—'}</dd></div>
                        <div><dt>Attempt</dt><dd>{selectedJob.execution_trace.trace_compact_summary.attempt_number ?? '—'}</dd></div>
                        <div><dt>Dominant stage</dt><dd>{selectedJob.execution_trace.trace_compact_summary.dominant_stage_name ?? '—'}</dd></div>
                        <div><dt>Heartbeat count</dt><dd>{selectedJob.execution_trace.trace_compact_summary.heartbeat_count ?? '—'}</dd></div>
                        <div><dt>Reclaim count</dt><dd>{selectedJob.execution_trace.trace_compact_summary.reclaim_count ?? '—'}</dd></div>
                        <div><dt>Progress span</dt><dd>{selectedJob.execution_trace.trace_compact_summary.progress_span_percent ?? '—'}</dd></div>
                        <div><dt>Last stage label</dt><dd>{selectedJob.execution_trace.trace_compact_summary.last_stage_label ?? '—'}</dd></div>
                        <div><dt>Average progress</dt><dd>{selectedJob.execution_trace.trace_compact_summary.average_progress_percent ?? '—'}</dd></div>
                        <div><dt>Unique transition tags</dt><dd>{selectedJob.execution_trace.trace_compact_summary.unique_transition_tag_count ?? '—'}</dd></div>
                        <div><dt>Latest transition tag</dt><dd>{selectedJob.execution_trace.trace_compact_summary.latest_transition_tag ?? '—'}</dd></div>
                        <div><dt>Worker count</dt><dd>{selectedJob.execution_trace.trace_compact_summary.worker_count ?? '—'}</dd></div>
                        <div><dt>Worker metadata keys</dt><dd>{selectedJob.execution_trace.trace_compact_summary.worker_metadata_key_count ?? '—'}</dd></div>
                        <div><dt>Latest worker metadata keys</dt><dd>{selectedJob.execution_trace.trace_compact_summary.latest_worker_metadata_keys?.join(', ') ?? '—'}</dd></div>
                      </dl>
                    ) : (
                      <p className="muted">У этой job ещё нет compact trace summary.</p>
                    )}
                  </div>

                  <div className="stack-sm">
                    <div className="section-header compact-header">
                      <div>
                        <h3>Result text</h3>
                        <p className="muted">Сводный `output_text`, который worker сохранил в job record.</p>
                      </div>
                    </div>
                    {selectedJob.output_text ? (
                      <pre className="code-block">{selectedJob.output_text}</pre>
                    ) : (
                      <p className="muted">У этой job ещё нет сохранённого `output_text`.</p>
                    )}
                  </div>

                  <div className="stack-sm">
                    <div className="section-header compact-header">
                      <div>
                        <h3>Artifact</h3>
                        <p className="muted">Authenticated readback через `/api/v1/jobs/{'{job_id}'}/artifact`.</p>
                      </div>
                      {selectedJob.output_artifact_key ? (
                        <button
                          className="secondary-button"
                          disabled={isArtifactDownloading}
                          onClick={handleDownloadArtifact}
                          type="button"
                        >
                          {isArtifactDownloading ? 'Скачиваем…' : 'Скачать artifact'}
                        </button>
                      ) : null}
                    </div>

                    <dl className="keyvals">
                      <div><dt>Artifact key</dt><dd className="mono">{selectedJob.output_artifact_key ?? '—'}</dd></div>
                      <div><dt>Artifact URL</dt><dd className="mono">{selectedJob.output_artifact_url ?? '—'}</dd></div>
                      <div><dt>Content type</dt><dd>{artifactContentType ?? selectedJob.output_artifact_content_type ?? '—'}</dd></div>
                      <div><dt>Size</dt><dd>{selectedJob.output_artifact_size_bytes ?? '—'}</dd></div>
                      <div><dt>ETag</dt><dd className="mono">{selectedJob.output_artifact_etag ?? '—'}</dd></div>
                    </dl>

                    {artifactError ? <p className="error-text">{artifactError}</p> : null}
                    {isArtifactLoading ? <p className="muted">Загружаем artifact preview…</p> : null}

                    {selectedJob.output_artifact_key ? (
                      canPreviewArtifact(artifactContentType ?? selectedJob.output_artifact_content_type) ? (
                        artifactText ? (
                          <pre className="code-block">{artifactText}</pre>
                        ) : (
                          !isArtifactLoading && <p className="muted">Artifact доступен, но preview пока пустой.</p>
                        )
                      ) : (
                        <p className="muted">Для этого content type preview не рисуем, но artifact можно скачать кнопкой выше.</p>
                      )
                    ) : (
                      <p className="muted">У этой job ещё нет сохранённого artifact.</p>
                    )}
                  </div>
                </article>
              </div>
            ) : null}
          </section>

          <section className="card stack-md">
            <div className="section-header">
              <div>
                <h2>Memberships</h2>
                <p className="muted">Реальные membership записи из backend, которые задают scope для brief/job flows.</p>
              </div>
              <span className="pill">{memberships.length}</span>
            </div>

            {memberships.length === 0 ? (
              <p className="muted">У пользователя пока нет организаций. Следующий слой UI должен корректно обрабатывать этот кейс.</p>
            ) : (
              <div className="table-like stack-sm">
                {memberships.map((membership) => (
                  <div className="row" key={`${membership.organization_id}-${membership.role}`}>
                    <div><div className="row-label">Organization</div><div className="row-value mono">{membership.organization_id}</div></div>
                    <div><div className="row-label">Role</div><div className="row-value">{membership.role}</div></div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
