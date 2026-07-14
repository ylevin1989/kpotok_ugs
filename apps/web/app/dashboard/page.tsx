'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { loadSession, loadScopeSelection, saveScopeSelection } from '../../lib/auth';
import { getOrganizations, getBrands, getProducts, getContentPlans, getAudienceSegments } from '../../lib/api';
import type { OrganizationRead, BrandRead, ProductRead, ContentPlanRead, AudienceSegmentRead } from '../../lib/types';

interface BrandAgg { brand: BrandRead; products: number; plans: number; audiences: number; }

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [orgs, setOrgs] = useState<OrganizationRead[]>([]);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [rows, setRows] = useState<BrandAgg[]>([]);
  const [plans, setPlans] = useState<ContentPlanRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const s = loadSession();
    if (!s) { router.push('/login'); return; }
    setToken(s.accessToken);
    getOrganizations(s.accessToken)
      .then((r) => {
        setOrgs(r.items);
        const saved = loadScopeSelection();
        const initial = saved?.organizationId && r.items.some((o) => o.id === saved.organizationId)
          ? saved.organizationId
          : r.items[0]?.id ?? null;
        setOrgId(initial);
        if (!initial) setLoading(false);
      })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, [router]);

  useEffect(() => {
    if (!token || !orgId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const brandsResp = await getBrands(token, orgId);
        const aggs: BrandAgg[] = [];
        const allPlans: ContentPlanRead[] = [];
        for (const brand of brandsResp.items) {
          const [p, pl, au] = await Promise.all([
            getProducts(token, orgId, brand.id).catch(() => ({ items: [] as ProductRead[] })),
            getContentPlans(token, orgId, brand.id).catch(() => ({ items: [] as ContentPlanRead[] })),
            getAudienceSegments(token, orgId, brand.id).catch(() => ({ items: [] as AudienceSegmentRead[] })),
          ]);
          aggs.push({ brand, products: p.items.length, plans: pl.items.length, audiences: au.items.length });
          allPlans.push(...pl.items);
        }
        if (cancelled) return;
        setRows(aggs);
        allPlans.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
        setPlans(allPlans.slice(0, 6));
      } catch (e) {
        if (!cancelled) setError(String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token, orgId]);

  const totals = useMemo(() => ({
    brands: rows.length,
    products: rows.reduce((s, r) => s + r.products, 0),
    audiences: rows.reduce((s, r) => s + r.audiences, 0),
    plans: rows.reduce((s, r) => s + r.plans, 0),
    dna: rows.filter((r) => r.brand.dna_json).length,
  }), [rows]);

  function pickOrg(id: string) {
    setOrgId(id);
    saveScopeSelection({ organizationId: id, brandId: null });
  }

  return (
    <div className="stack-lg">
      <div className="section-header">
        <div className="stack-xs">
          <span className="eyebrow">Обзор</span>
          <h1>Дашборд</h1>
          <p className="muted">Сводка по организации: бренды, товары, аудитории и контент-планы.</p>
        </div>
        {orgs.length > 0 && (
          <label className="label-stack" style={{ minWidth: 240 }}>
            <span>Организация</span>
            <select className="input" value={orgId ?? ''} onChange={(e) => pickOrg(e.target.value)}>
              {orgs.map((o) => (<option key={o.id} value={o.id}>{o.name}</option>))}
            </select>
          </label>
        )}
      </div>

      {error && <div className="error-card">{error}</div>}

      <div className="stat-grid">
        <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Организации</div><div className="stat-value">{orgs.length}</div><div className="stat-hint">всего доступно</div></div>
        <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Бренды</div><div className="stat-value">{totals.brands}</div><div className="stat-hint">{totals.dna} с готовой ДНК</div></div>
        <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Товары</div><div className="stat-value">{totals.products}</div><div className="stat-hint">в текущей организации</div></div>
        <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Аудитории</div><div className="stat-value">{totals.audiences}</div><div className="stat-hint">сегментов ЦА</div></div>
        <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Контент-планы</div><div className="stat-value">{totals.plans}</div><div className="stat-hint">строк планов</div></div>
      </div>

      <div className="card stack-md">
        <div className="section-header">
          <h2>Бренды</h2>
          <Link href="/brands" className="secondary-button">Все бренды →</Link>
        </div>
        {loading ? (
          <p className="muted">Загрузка…</p>
        ) : rows.length === 0 ? (
          <div className="empty">В этой организации ещё нет брендов. <Link href="/brands" className="pill">Создать бренд</Link></div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Бренд</th><th>Товары</th><th>Аудитории</th><th>Планы</th><th>Brand DNA</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.brand.id}>
                    <td><strong>{r.brand.name}</strong><div className="faint mono">{r.brand.slug}</div></td>
                    <td>{r.products}</td>
                    <td>{r.audiences}</td>
                    <td>{r.plans}</td>
                    <td>{r.brand.dna_json ? <span className="badge ok">готова</span> : <span className="badge warn">нет</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card stack-md">
        <div className="section-header">
          <h2>Недавние контент-планы</h2>
          <Link href="/content-plans" className="secondary-button">Все планы →</Link>
        </div>
        {plans.length === 0 ? (
          <div className="empty">Пока нет контент-планов.</div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Дата</th><th>Заголовок</th><th>Площадка</th><th>Тип</th><th>Статус</th></tr></thead>
              <tbody>
                {plans.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.date}</td>
                    <td>{p.title}</td>
                    <td><span className="pill">{p.platform}</span></td>
                    <td className="muted">{p.content_type}</td>
                    <td><span className="badge info">{p.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
