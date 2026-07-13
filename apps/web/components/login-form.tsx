'use client';

import type { FormEvent } from 'react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { saveSession } from '../lib/auth';
import { login } from '../lib/api';

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await login(email, password);
      saveSession({ accessToken: response.access_token, userEmail: response.user.email });
      router.replace('/onboarding');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить вход');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="form-grid" onSubmit={handleSubmit}>
      <label className="label-stack">
        <span>Email</span>
        <input
          autoComplete="email"
          className="input"
          onChange={(event) => setEmail(event.target.value)}
          placeholder="owner@example.com"
          required
          type="email"
          value={email}
        />
      </label>

      <label className="label-stack">
        <span>Пароль</span>
        <input
          autoComplete="current-password"
          className="input"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="••••••••"
          required
          type="password"
          value={password}
        />
      </label>

      {error ? <p className="error-text">{error}</p> : null}

      <button className="primary-button" disabled={isSubmitting} type="submit">
        {isSubmitting ? 'Входим…' : 'Войти'}
      </button>
    </form>
  );
}
