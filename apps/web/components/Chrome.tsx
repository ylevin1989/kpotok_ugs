'use client';

import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState, type ReactNode } from 'react';
import { clearScopeSelection, clearSession, loadScopeSelection, loadSession, saveScopeSelection } from '../lib/auth';
import { getOrganizations, getBrands } from '../lib/api';
import type { OrganizationRead, BrandRead } from '../lib/types';

const BARE_ROUTES = new Set(['/', '/login', '/register']);

const NAV: { group: string; items: { href: string; label: string; ic: string }[] }[] = [
  { group: 'Обзор', items: [{ href: '/dashboard', label: 'Дашборд', ic: '◉' }] },
  { group: 'Контент', items: [
    { href: '/brands', label: 'Бренды', ic: '❖' },
    { href: '/products', label: 'Товары', ic: '▤' },
    { href: '/audience-segments', label: 'Аудитории', ic: '◐' },
    { href: '/content-plans', label: 'Контент-планы', ic: '▦' },
    { href: '/production-flow', label: 'Производство', ic: '⚙' },
    { href: '/media-assets', label: 'Медиатека', ic: '❏' },
    { href: '/studio', label: 'Медиа-студия', ic: '✦' },
    { href: '/references', label: 'Референсы', ic: '❑' },
  ] },
  { group: 'Управление', items: [
    { href: '/members', label: 'Участники', ic: '◍' },
    { href: '/subscriptions', label: 'Тариф', ic: '◆' },
    { href: '/support', label: 'Поддержка', ic: '☂' },
    { href: '/admin', label: 'Админка', ic: '⚑' },
  ] },
];

const TITLES: Record<string, string> = {
  '/dashboard': 'Дашборд', '/brands': 'Бренды', '/products': 'Товары',
  '/audience-segments': 'Аудитории', '/content-plans': 'Контент-планы',
  '/production-flow': 'Производство', '/media-assets': 'Медиатека', '/studio': 'Медиа-студия', '/references': 'Референсы',
  '/members': 'Участники', '/subscriptions': 'Тариф и лимиты',
  '/support': 'Поддержка', '/admin': 'Админ-панель', '/onboarding': 'Онбординг',
};

export default function Chrome({ children }: { children: ReactNode }) {
  const pathname = usePathname() || '/';
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [orgs, setOrgs] = useState<OrganizationRead[]>([]);
  const [brands, setBrands] = useState<BrandRead[]>([]);
  const [orgId, setOrgId] = useState<string>('');
  const [brandId, setBrandId] = useState<string>('');

  const bare = BARE_ROUTES.has(pathname);

  useEffect(() => {
    if (bare) return;
    const s = loadSession();
    if (!s) return;
    setEmail(s.userEmail);
    setToken(s.accessToken);
    getOrganizations(s.accessToken).then((r) => {
      setOrgs(r.items);
      const saved = loadScopeSelection();
      const oid = saved?.organizationId && r.items.some((o) => o.id === saved.organizationId) ? saved.organizationId : r.items[0]?.id ?? '';
      setOrgId(oid);
    }).catch(() => {});
  }, [bare, pathname]);

  useEffect(() => {
    if (!token || !orgId) return;
    getBrands(token, orgId).then((r) => {
      setBrands(r.items);
      const saved = loadScopeSelection();
      const bid = saved?.brandId && r.items.some((b) => b.id === saved.brandId) ? saved.brandId : r.items[0]?.id ?? '';
      setBrandId(bid);
      saveScopeSelection({ organizationId: orgId, brandId: bid || null });
    }).catch(() => {});
  }, [token, orgId]);

  if (bare) return <>{children}</>;

  const title = TITLES[pathname] ?? 'Content Factory';
  const initial = (email ?? 'U').charAt(0).toUpperCase();

  function logout() { clearSession(); clearScopeSelection(); router.push('/login'); }
  function changeOrg(id: string) { saveScopeSelection({ organizationId: id, brandId: null }); window.location.reload(); }
  function changeBrand(id: string) { saveScopeSelection({ organizationId: orgId, brandId: id || null }); window.location.reload(); }

  return (
    <div className="layout">
      <aside className={open ? 'sidebar open' : 'sidebar'}>
        <div className="brand-mark">
          <div className="brand-logo">CF</div>
          <div><div className="brand-name">Контент-завод</div><div className="brand-sub">AI Content Ops</div></div>
        </div>
        {NAV.map((g) => (
          <div key={g.group}>
            <div className="nav-group-label">{g.group}</div>
            {g.items.map((it) => {
              const active = pathname === it.href || pathname.startsWith(it.href + '/');
              return (
                <Link key={it.href} href={it.href} className={active ? 'nav-item active' : 'nav-item'} onClick={() => setOpen(false)}>
                  <span className="ic">{it.ic}</span><span>{it.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
        <div className="sidebar-foot">
          <button className="nav-item" style={{ width: '100%', border: 'none', background: 'transparent' }} onClick={logout}>
            <span className="ic">⏻</span><span>Выйти</span>
          </button>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="ghost-button" style={{ minHeight: 34, padding: '6px 10px' }} onClick={() => setOpen((v) => !v)} aria-label="Меню">☰</button>
            <span className="topbar-title">{title}</span>
          </div>
          <div className="topbar-right">
            {orgs.length > 0 && (
              <select className="input" style={{ minHeight: 36, maxWidth: 180 }} value={orgId} onChange={(e) => changeOrg(e.target.value)} title="Организация">
                {orgs.map((o) => (<option key={o.id} value={o.id}>{o.name}</option>))}
              </select>
            )}
            {brands.length > 0 && (
              <select className="input" style={{ minHeight: 36, maxWidth: 180 }} value={brandId} onChange={(e) => changeBrand(e.target.value)} title="Бренд">
                {brands.map((b) => (<option key={b.id} value={b.id}>{b.name}</option>))}
              </select>
            )}
            <div className="user-chip"><span className="avatar">{initial}</span><span className="muted">{email ?? '—'}</span></div>
          </div>
        </header>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
