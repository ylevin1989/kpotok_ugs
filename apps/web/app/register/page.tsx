import Link from 'next/link';
import { RegisterForm } from '../../components/register-form';

export default function RegisterPage() {
  return (
    <main className="centered-page">
      <section className="card stack-lg auth-card">
        <div className="stack-sm">
          <span className="eyebrow">Client onboarding</span>
          <h1>Регистрация в Content Factory</h1>
          <p className="muted">
            Самостоятельная регистрация для новых пользователей. После входа откроется onboarding-мастер и затем рабочий кабинет.
          </p>
        </div>
        <RegisterForm />
        <p className="muted">
          Уже есть аккаунт? <Link href="/login">Войти</Link>
        </p>
      </section>
    </main>
  );
}
