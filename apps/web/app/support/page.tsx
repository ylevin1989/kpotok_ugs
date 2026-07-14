'use client';

import type { FormEvent } from 'react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getMe, lookupSupportUser } from '../../lib/api';
import { loadSession } from '../../lib/auth';
import type { MeResponse, SupportUserLookupResponse } from '../../lib/types';

const SUPPORT_ROLES = new Set(['super_admin', 'platform_admin']);

function formatPlatformRole(role: string | null | undefined): string {
  const map: Record<string, string> = {
    super_admin: 'суперадминистратор',
    platform_admin: 'администратор платформы',
    client_owner: 'владелец клиента',
    client_manager: 'менеджер клиента',
    client_reviewer: 'ревьюер клиента',
  };
  return role ? map[role] ?? role : '—';
}

function formatOrganizationStatus(status: string | null | undefined): string {
  const map: Record<string, string> = {
    active: 'активна',
    inactive: 'неактивна',
    pending: 'ожидает',
  };
  return status ? map[status] ?? status : '—';
}

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
          <span className="eyebrow">Поддержка оператора</span>
          <h1>Поиск восстановления и поддержки</h1>
          <p className="muted">
            Быстрый операторский поиск пользователя по электронной почте: профиль, роль платформы и членства по организациям.
          </p>
        </div>
        <div className="row">
          <Link className="secondary-button" href="/dashboard">Панель</Link>
          <Link className="secondary-button" href="/members">Участники</Link>
        </div>
      </section>

      {loading ? <section className="card stack-sm"><p className="muted">Проверяем операторский доступ…</p></section> : null}
      {error ? <section className="card stack-sm error-card"><p>{error}</p></section> : null}

      {me && !canUseSupport ? (
        <section className="card stack-sm error-card">
          <h2>Недостаточно прав</h2>
          <p>Эта страница доступна только super_admin и platform_admin.</p>
          <p className="muted">Текущий platform role: {formatPlatformRole(me.user.platform_role)}</p>
        </section>
      ) : null}

      {canUseSupport ? (
        <>
          <section className="card stack-md">
            <h2>Поиск пользователя</h2>
            <form className="stack-md" onSubmit={handleSubmit}>
              <label className="label-stack">
                <span>Электронная почта</span>
                <input
                  className="input"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="пользователь@пример.рф"
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
                <h2>Профиль пользователя</h2>
                <dl className="keyvals">
                  <div><dt>Электронная почта</dt><dd>{result.user.email}</dd></div>
                  <div><dt>Имя</dt><dd>{result.user.full_name ?? '—'}</dd></div>
                  <div><dt>Роль на платформе</dt><dd>{formatPlatformRole(result.user.platform_role)}</dd></div>
                  <div><dt>Активен</dt><dd>{result.user.is_active ? 'да' : 'нет'}</dd></div>
                  <div><dt>Создан</dt><dd>{new Date(result.user.created_at).toLocaleString('ru-RU')}</dd></div>
                </dl>
              </article>

              <article className="card stack-sm">
                <h2>Членства</h2>
                <div className="stack-sm">
                  {result.memberships.map((membership) => (
                    <article className="brief-card stack-xs" key={membership.organization_id}>
                      <div className="brief-meta">
                        <strong>{membership.organization_name}</strong>
                        <span className="pill subtle-pill">{formatPlatformRole(membership.role)}</span>
                      </div>
                      <p className="muted">{membership.organization_slug} · {formatOrganizationStatus(membership.organization_status)}</p>
                      <div className="row-label mono">{new Date(membership.created_at).toLocaleString('ru-RU')}</div>
                    </article>
                  ))}
                  {result.memberships.length === 0 ? <p className="muted">У пользователя нет членств.</p> : null}
                </div>
              </article>
            </section>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
