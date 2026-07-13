'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { loadSession } from '../lib/auth';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const session = loadSession();
    router.replace(session ? '/onboarding' : '/login');
  }, [router]);

  return (
    <main className="centered-page">
      <div className="card stack-md">
        <span className="eyebrow">Content Factory</span>
        <h1>Подготавливаем рабочее пространство</h1>
        <p className="muted">Проверяем сохранённую сессию и перенаправляем дальше.</p>
      </div>
    </main>
  );
}
