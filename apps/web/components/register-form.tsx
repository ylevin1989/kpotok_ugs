'use client';

import type { FormEvent } from 'react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { saveSession } from '../lib/auth';
import { register } from '../lib/api';

export function RegisterForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await register({
        email,
        full_name: fullName.trim() || null,
        password,
      });
      saveSession({ accessToken: response.access_token, userEmail: response.user.email });
      router.replace('/onboarding');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось зарегистрироваться');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="form-grid" onSubmit={handleSubmit}>
      <label className="label-stack">
        <span>Имя</span>
        <input
          autoComplete="name"
          className="input"
          onChange={(event) => setFullName(event.target.value)}
          placeholder="Яков"
          value={fullName}
        />
      </label>

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
          autoComplete="new-password"
          className="input"
          minLength={8}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Минимум 8 символов"
          required
          type="password"
          value={password}
        />
      </label>

      {error ? <p className="error-text">{error}</p> : null}

      <button className="primary-button" disabled={isSubmitting} type="submit">
        {isSubmitting ? 'Создаём аккаунт…' : 'Создать аккаунт'}
      </button>
    </form>
  );
}
