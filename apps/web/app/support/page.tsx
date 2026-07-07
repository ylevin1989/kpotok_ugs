'use client';

import type { FormEvent } from 'react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getMe, lookupSupportUser } from '../../lib/api';
import { loadSession } from '../../lib/auth';
import type { MeResponse, SupportUserLookupResponse } from '../../lib/types';

const SUPPORT_ROLES = new Set(['super_admin', 'platform_admin']);

export default function SupportPage() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [email, setEmail] = useState('');
  const [result, setResult] = useState<SupportUserLookupResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
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
        const response = await getMe(token);
        if (cancelled) {
          return;
        }
        setMe(response);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить профиль');
          router.replace('/login');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [router]);

  const canUseSupport = SUPPORT_ROLES.has(me?.user.platform_role ?? '');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      return;
    }

    setSearching(true);
    setError(null);
    try {
      const response = await lookupSupportUser(accessToken, email.trim());
      setResult(response);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : 'Не удалось выполнить поиск');
    } finally {
      setSearching(false);
    }
  }

  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Operator support</span>
          <h1>Recovery / support lookup</h1>
          <p className="muted">
            Быстрый операторский поиск пользователя по email: профиль, platform role и memberships по организациям.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Dashboard</Link>
          <Link className="secondary-button" href="/members">Members</Link>
        </div>
      </section>

      {loading ? <section className="card stack-sm"><p className="muted">Проверяем операторский доступ…</p></section> : null}
      {error ? <section className="card stack-sm error-card"><p>{error}</p></section> : null}

      {me && !canUseSupport ? (
        <section className="card stack-sm error-card">
          <h2>Недостаточно прав</h2>
          <p>Эта страница доступна только super_admin и platform_admin.</p>
          <p className="muted">Текущий platform role: {me.user.platform_role ?? '—'}</p>
        </section>
      ) : null}

      {canUseSupport ? (
        <>
          <section className="card stack-md">
            <h2>Lookup user</h2>
            <form className="stack-md" onSubmit={handleSubmit}>
              <label className="label-stack">
                <span>Email</span>
                <input
                  className="input"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="user@example.com"
                  required
                  type="email"
                  value={email}
                />
              </label>
              <button className="primary-button" disabled={searching} type="submit">
                {searching ? 'Ищем…' : 'Найти пользователя'}
              </button>
            </form>
          </section>

          {result ? (
            <section className="grid two-up briefs-grid">
              <article className="card stack-sm">
                <h2>User profile</h2>
                <dl className="keyvals">
                  <div><dt>Email</dt><dd>{result.user.email}</dd></div>
                  <div><dt>Name</dt><dd>{result.user.full_name ?? '—'}</dd></div>
                  <div><dt>Platform role</dt><dd>{result.user.platform_role ?? '—'}</dd></div>
                  <div><dt>Active</dt><dd>{result.user.is_active ? 'yes' : 'no'}</dd></div>
                  <div><dt>Created</dt><dd>{new Date(result.user.created_at).toLocaleString('ru-RU')}</dd></div>
                </dl>
              </article>

              <article className="card stack-sm">
                <h2>Memberships</h2>
                <div className="stack-sm">
                  {result.memberships.map((membership) => (
                    <article className="brief-card stack-xs" key={membership.organization_id}>
                      <div className="brief-meta">
                        <strong>{membership.organization_name}</strong>
                        <span className="pill subtle-pill">{membership.role}</span>
                      </div>
                      <p className="muted">{membership.organization_slug} · {membership.organization_status}</p>
                      <div className="row-label mono">{new Date(membership.created_at).toLocaleString('ru-RU')}</div>
                    </article>
                  ))}
                  {result.memberships.length === 0 ? <p className="muted">У пользователя нет memberships.</p> : null}
                </div>
              </article>
            </section>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
