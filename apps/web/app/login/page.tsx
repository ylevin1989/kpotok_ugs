import { LoginForm } from '../../components/login-form';

export default function LoginPage() {
  return (
    <main className="centered-page">
      <section className="card stack-lg auth-card">
        <div className="stack-sm">
          <span className="eyebrow">MVP auth shell</span>
          <h1>Вход в Content Factory</h1>
          <p className="muted">
            Это первый пользовательский слой поверх уже работающего backend/API. Логин идёт в
            существующий `apiha.uno-ai.pw`, без отдельного или вложенного Hermes runtime.
          </p>
        </div>
        <LoginForm />
      </section>
    </main>
  );
}
