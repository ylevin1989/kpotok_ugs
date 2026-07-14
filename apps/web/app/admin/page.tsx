'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { loadSession } from '../../lib/auth';
import {
  adminOverview, adminListOrganizations, adminListUsers,
  adminCreateOrganization, adminCreateBrand, adminAddMember, adminSetPlatformRole,
  type AdminOrg, type AdminUser,
} from '../../lib/api';

function slugify(s: string) { return s.toLowerCase().replace(/[^a-z0-9а-я]+/gi, '-').replace(/(^-|-$)/g, '') + '-' + Date.now().toString().slice(-5); }

export default function AdminPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [ov, setOv] = useState<{ organizations: number; brands: number; products: number; users: number } | null>(null);
  const [orgs, setOrgs] = useState<AdminOrg[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const [orgName, setOrgName] = useState(''); const [orgOwner, setOrgOwner] = useState('');
  const [brOrg, setBrOrg] = useState(''); const [brName, setBrName] = useState('');
  const [memOrg, setMemOrg] = useState(''); const [memEmail, setMemEmail] = useState(''); const [memRole, setMemRole] = useState('client_manager');

  async function reload(t: string) {
    try {
      const [o, org, us] = await Promise.all([adminOverview(t), adminListOrganizations(t), adminListUsers(t)]);
      setOv(o); setOrgs(org.items); setUsers(us.items); setForbidden(false);
    } catch (e) {
      if (String(e).includes('403')) setForbidden(true); else setErr(String(e));
    }
  }

  useEffect(() => {
    const s = loadSession();
    if (!s) { router.push('/login'); return; }
    setToken(s.accessToken);
    reload(s.accessToken);
  }, [router]);

  function flash(m: string) { setMsg(m); setErr(null); setTimeout(() => setMsg(null), 4000); }
  function fail(e: unknown) { setErr(String(e)); }

  async function doCreateOrg() {
    if (!token || !orgName || !orgOwner) return;
    try { await adminCreateOrganization(token, { name: orgName, slug: slugify(orgName), owner_email: orgOwner.trim() }); flash('Организация создана и назначен владелец'); setOrgName(''); setOrgOwner(''); reload(token); } catch (e) { fail(e); }
  }
  async function doCreateBrand() {
    if (!token || !brOrg || !brName) return;
    try { await adminCreateBrand(token, { organization_id: brOrg, name: brName, slug: slugify(brName) }); flash('Бренд создан'); setBrName(''); reload(token); } catch (e) { fail(e); }
  }
  async function doAddMember() {
    if (!token || !memOrg || !memEmail) return;
    try { await adminAddMember(token, { organization_id: memOrg, user_email: memEmail.trim(), role: memRole }); flash('Участник добавлен'); setMemEmail(''); reload(token); } catch (e) { fail(e); }
  }
  async function setRole(userId: string, role: string | null) {
    if (!token) return;
    try { await adminSetPlatformRole(token, userId, role); flash('Роль обновлена'); reload(token); } catch (e) { fail(e); }
  }

  if (forbidden) {
    return (
      <div className="card">
        <h2>Нет доступа</h2>
        <p className="muted">Раздел доступен только платформенным администраторам (super_admin / platform_admin).</p>
      </div>
    );
  }

  return (
    <div className="stack-lg">
      <div className="stack-xs">
        <span className="eyebrow">Платформа</span>
        <h1>Админ-панель</h1>
        <p className="muted">Все организации, бренды и пользователи. Провижининг: создать организацию для пользователя, бренд для организации, назначить роли.</p>
      </div>

      {msg && <div className="card" style={{ borderColor: 'rgba(69,208,158,0.4)' }}><span className="badge ok">{msg}</span></div>}
      {err && <div className="error-card">{err}</div>}

      {ov && (
        <div className="stat-grid">
          <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Организации</div><div className="stat-value">{ov.organizations}</div></div>
          <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Бренды</div><div className="stat-value">{ov.brands}</div></div>
          <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Товары</div><div className="stat-value">{ov.products}</div></div>
          <div className="stat-tile"><div className="stat-label"><span className="stat-dot" />Пользователи</div><div className="stat-value">{ov.users}</div></div>
        </div>
      )}

      <div className="grid two-up">
        <div className="card stack-md">
          <h2>Создать организацию для пользователя</h2>
          <label className="label-stack"><span>Название организации</span><input className="input" value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Моя компания" /></label>
          <label className="label-stack"><span>Email владельца (зарегистрированного пользователя)</span><input className="input" value={orgOwner} onChange={(e) => setOrgOwner(e.target.value)} placeholder="user@example.com" /></label>
          <button className="primary-button" onClick={doCreateOrg}>Создать организацию</button>
        </div>
        <div className="card stack-md">
          <h2>Создать бренд в организации</h2>
          <label className="label-stack"><span>Организация</span>
            <select className="input" value={brOrg} onChange={(e) => setBrOrg(e.target.value)}>
              <option value="">— выбери —</option>
              {orgs.map((o) => (<option key={o.id} value={o.id}>{o.name}</option>))}
            </select>
          </label>
          <label className="label-stack"><span>Название бренда</span><input className="input" value={brName} onChange={(e) => setBrName(e.target.value)} placeholder="Мой бренд" /></label>
          <button className="primary-button" onClick={doCreateBrand}>Создать бренд</button>
        </div>
      </div>

      <div className="card stack-md">
        <h2>Добавить участника в организацию</h2>
        <div className="grid two-up">
          <label className="label-stack"><span>Организация</span>
            <select className="input" value={memOrg} onChange={(e) => setMemOrg(e.target.value)}>
              <option value="">— выбери —</option>
              {orgs.map((o) => (<option key={o.id} value={o.id}>{o.name}</option>))}
            </select>
          </label>
          <label className="label-stack"><span>Email пользователя</span><input className="input" value={memEmail} onChange={(e) => setMemEmail(e.target.value)} placeholder="user@example.com" /></label>
          <label className="label-stack"><span>Роль</span>
            <select className="input" value={memRole} onChange={(e) => setMemRole(e.target.value)}>
              <option value="client_owner">Владелец</option>
              <option value="client_manager">Менеджер</option>
              <option value="client_reviewer">Согласующий</option>
            </select>
          </label>
        </div>
        <button className="primary-button" style={{ width: 'fit-content' }} onClick={doAddMember}>Добавить участника</button>
      </div>

      <div className="card stack-md">
        <div className="section-header"><h2>Организации ({orgs.length})</h2></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Организация</th><th>Бренды</th><th>Товары</th><th>Участники</th><th>Владельцы</th></tr></thead>
            <tbody>
              {orgs.map((o) => (
                <tr key={o.id}>
                  <td><strong>{o.name}</strong><div className="faint mono">{o.slug}</div></td>
                  <td>{o.brands}</td><td>{o.products}</td><td>{o.members}</td>
                  <td className="muted">{o.owners.join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card stack-md">
        <div className="section-header"><h2>Пользователи ({users.length})</h2></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Email</th><th>Платформенная роль</th><th>Организаций</th><th>Действия</th></tr></thead>
            <tbody>
              {users.slice(0, 100).map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.platform_role ? <span className="badge info">{u.platform_role}</span> : <span className="faint">—</span>}</td>
                  <td>{u.organizations}</td>
                  <td style={{ display: 'flex', gap: 8 }}>
                    {u.platform_role ? (
                      <button className="secondary-button" style={{ minHeight: 32, padding: '4px 10px' }} onClick={() => setRole(u.id, null)}>Снять админа</button>
                    ) : (
                      <button className="secondary-button" style={{ minHeight: 32, padding: '4px 10px' }} onClick={() => setRole(u.id, 'platform_admin')}>Сделать админом</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
