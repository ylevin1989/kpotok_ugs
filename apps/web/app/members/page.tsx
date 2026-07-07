'use client';

import { useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  createOrganizationMember,
  deleteOrganizationMember,
  getOrganizationMembers,
  getOrganizationPermissionEvents,
  getOrganizations,
  updateOrganizationMember,
} from '../../lib/api';
import { loadSession } from '../../lib/auth';
import type {
  OrganizationMemberRead,
  OrganizationPermissionEventRead,
  OrganizationRead,
} from '../../lib/types';

const ROLE_OPTIONS = [
  { value: 'client_owner', label: 'Owner' },
  { value: 'client_manager', label: 'Manager' },
  { value: 'client_reviewer', label: 'Reviewer' },
] as const;

export default function MembersPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationRead[]>([]);
  const [organizationId, setOrganizationId] = useState('');
  const [members, setMembers] = useState<OrganizationMemberRead[]>([]);
  const [events, setEvents] = useState<OrganizationPermissionEventRead[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<(typeof ROLE_OPTIONS)[number]['value']>('client_manager');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selectedOrganization = organizations.find((item) => item.id === organizationId) ?? null;

  useEffect(() => {
    const session = loadSession();
    if (!session) {
      router.replace('/login');
      return;
    }

    setAccessToken(session.accessToken);
  }, [router]);

  useEffect(() => {
    const token = accessToken as string;
    if (!accessToken) {
      return;
    }

    let cancelled = false;
    async function loadOrganizations() {
      setLoading(true);
      setError(null);
      try {
        const response = await getOrganizations(token!);
        if (cancelled) return;
        setOrganizations(response.items);
        if (response.items.length > 0 && !organizationId) {
          setOrganizationId(response.items[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить организации');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadOrganizations();
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  useEffect(() => {
    const token = accessToken as string;
    const organization = organizationId as string;
    if (!token || !organization) {
      setMembers([]);
      setEvents([]);
      return;
    }

    let cancelled = false;
    async function loadMembers() {
      setLoading(true);
      setError(null);
      try {
        const [membersResponse, eventsResponse] = await Promise.all([
          getOrganizationMembers(token!, organization!),
          getOrganizationPermissionEvents(token!, organization!),
        ]);
        if (cancelled) return;
        setMembers(membersResponse.items);
        setEvents(eventsResponse.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить members');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadMembers();
    return () => {
      cancelled = true;
    };
  }, [accessToken, organizationId]);

  async function handleInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !organizationId) {
      return;
    }
    const token = accessToken as string;
    const organization = organizationId as string;
    setActionError(null);
    setSuccess(null);
    try {
      const created = await createOrganizationMember(token, organization, { email, role });
      setMembers((current) => [...current, created]);
      setEmail('');
      setRole('client_manager');
      setSuccess(`Добавлен ${created.email} как ${created.role}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Не удалось добавить member');
    }
  }

  async function handleRoleChange(member: OrganizationMemberRead, nextRole: string) {
    if (!accessToken || !organizationId) {
      return;
    }
    const token = accessToken as string;
    const organization = organizationId as string;
    setActionError(null);
    setSuccess(null);
    try {
      const updated = await updateOrganizationMember(token, organization, member.id, { role: nextRole });
      setMembers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSuccess(`Роль ${updated.email} обновлена на ${updated.role}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Не удалось обновить роль');
    }
  }

  async function handleDelete(member: OrganizationMemberRead) {
    if (!accessToken || !organizationId) {
      return;
    }
    const token = accessToken as string;
    const organization = organizationId as string;
    setActionError(null);
    setSuccess(null);
    try {
      await deleteOrganizationMember(token, organization, member.id);
      setMembers((current) => current.filter((item) => item.id !== member.id));
      setSuccess(`Удалён ${member.email}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Не удалось удалить member');
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Organization access</span>
          <h1>Members / invitations</h1>
          <p className="muted">
            Управляй доступом через server-side membership roles. Здесь можно пригласить пользователя по email, поменять роль и посмотреть permission events.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Dashboard</Link>
          <Link className="secondary-button" href="/onboarding">Onboarding</Link>
        </div>
      </section>

      {!accessToken ? (
        <section className="card stack-sm error-card">
          <h2>Сессия не найдена</h2>
          <p>Сначала войди в систему.</p>
          <Link className="primary-button" href="/login">Войти</Link>
        </section>
      ) : null}

      {loading ? <section className="card stack-sm"><p className="muted">Загружаем members…</p></section> : null}
      {error ? <section className="card stack-sm error-card"><p>{error}</p></section> : null}
      {actionError ? <section className="card stack-sm error-card"><p>{actionError}</p></section> : null}
      {success ? <section className="card stack-sm"><p>{success}</p></section> : null}

      <section className="grid two-up briefs-grid">
        <article className="card stack-md">
          <h2>Choose organization</h2>
          <label className="label-stack">
            <span>Organization</span>
            <select className="input" onChange={(event) => setOrganizationId(event.target.value)} value={organizationId}>
              {organizations.length === 0 ? <option value="">Нет доступных организаций</option> : null}
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name} · {organization.membership_role} · {organization.status}
                </option>
              ))}
            </select>
          </label>
          <p className="muted">Фронтенд использует server roles без отдельной локальной модели прав.</p>
          <dl className="keyvals">
            <div><dt>Membership role</dt><dd>{selectedOrganization?.membership_role ?? '—'}</dd></div>
            <div><dt>Accessible members</dt><dd>{members.length}</dd></div>
            <div><dt>Permission events</dt><dd>{events.length}</dd></div>
          </dl>
        </article>

        <article className="card stack-md">
          <h2>Invite / add member</h2>
          <form className="stack-md" onSubmit={handleInvite}>
            <label className="label-stack">
              <span>Email</span>
              <input className="input" onChange={(event) => setEmail(event.target.value)} placeholder="teammate@example.com" required type="email" value={email} />
            </label>
            <label className="label-stack">
              <span>Role</span>
              <select className="input" onChange={(event) => setRole(event.target.value as typeof role)} value={role}>
                {ROLE_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
            <button className="primary-button" type="submit">Invite member</button>
          </form>
          <p className="muted">Сейчас API принимает только уже зарегистрированного пользователя по email. Самостоятельная регистрация — на отдельном экране.</p>
        </article>
      </section>

      <section className="grid two-up briefs-grid">
        <article className="card stack-md">
          <div className="section-header">
            <h2>Members</h2>
            <span className="pill">{members.length}</span>
          </div>
          <div className="stack-sm">
            {members.map((member) => (
              <article className="brief-card stack-sm" key={member.id}>
                <div className="brief-meta">
                  <strong>{member.email}</strong>
                  <span className="pill subtle-pill">{member.role}</span>
                </div>
                <div className="row-label mono">{member.user_id}</div>
                <div className="row">
                  <select className="input" onChange={(event) => handleRoleChange(member, event.target.value)} value={member.role}>
                    {ROLE_OPTIONS.map((item) => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </select>
                  <button className="secondary-button" onClick={() => handleDelete(member)} type="button">Delete</button>
                </div>
              </article>
            ))}
            {members.length === 0 ? <p className="muted">Пока нет members для выбранной организации.</p> : null}
          </div>
        </article>

        <article className="card stack-md">
          <div className="section-header">
            <h2>Permission events</h2>
            <span className="pill">{events.length}</span>
          </div>
          <div className="stack-sm">
            {events.map((eventItem) => (
              <article className="brief-card stack-xs" key={eventItem.id}>
                <div className="brief-meta">
                  <strong>{eventItem.action}</strong>
                  <span className="pill subtle-pill">{eventItem.actor_membership_role}</span>
                </div>
                <p className="muted">{eventItem.target_type} · {eventItem.target_id}</p>
                <div className="row-label mono">{new Date(eventItem.created_at).toLocaleString('ru-RU')}</div>
              </article>
            ))}
            {events.length === 0 ? <p className="muted">Permission events пока пусты.</p> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
