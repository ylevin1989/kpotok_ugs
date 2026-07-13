import Link from 'next/link';
import { LoginForm } from '../../components/login-form';

export default function LoginPage() {
  return (
    <main className="centered-page">
      <section className="card stack-lg auth-card">
        <div className="stack-sm">
          <span className="eyebrow">Вход и стартовый маршрут</span>
          <h1>Вход в Content Factory</h1>
          <p className="muted">
            После входа ты попадёшь в onboarding с прямыми ссылками на dashboard, brands и остальные рабочие экраны.
          </p>
        </div>
        <LoginForm />
        <p className="muted">
          Нет аккаунта? <Link href="/register">Зарегистрироваться</Link>
        </p>
      </section>
    </main>
  );
}
