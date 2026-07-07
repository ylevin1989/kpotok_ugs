import Link from 'next/link';

const steps = [
  {
    title: '1. Войти или зарегистрироваться',
    description: 'Создай аккаунт или зайди в существующий, чтобы получить доступ к организации и её рабочему scope.',
    href: '/register',
    label: 'Регистрация',
  },
  {
    title: '2. Открыть dashboard и выбрать organization',
    description: 'Dashboard подтягивает доступные memberships и даёт выбрать рабочий контекст.',
    href: '/dashboard',
    label: 'Dashboard',
  },
  {
    title: '3. Завести бренд и сгенерировать Brand DNA',
    description: 'Бренд — база для tone of voice, ограничений и генерации контента.',
    href: '/brands',
    label: 'Brands',
  },
  {
    title: '4. Добавить товары и запустить Product DNA',
    description: 'Товарные карточки собирают SKU, описание, преимущества, доказательства и ограничения.',
    href: '/products',
    label: 'Products',
  },
  {
    title: '5. Загрузить медиа и описать ЦА',
    description: 'Медиатека и аудитории дают контекст для контент-планов и материалов.',
    href: '/media-assets',
    label: 'Media',
  },
  {
    title: '6. Собрать контент-план и пройти quality-check',
    description: 'План, карточка материала, версии и тикеты — конечный рабочий цикл.',
    href: '/content-plans',
    label: 'Plans',
  },
];

export default function OnboardingPage() {
  return (
    <main className="page stack-xl">
      <section className="hero-row">
        <div className="stack-sm">
          <span className="eyebrow">Client onboarding</span>
          <h1>Onboarding-мастер</h1>
          <p className="muted">
            Быстрый маршрут от пустого кабинета до первого опубликованного материала. Роли владельца/менеджера/ревьюера уже учитываются на backend и в UI.
          </p>
        </div>
        <div className="row">
          <Link className="primary-button" href="/dashboard">Открыть dashboard</Link>
          <Link className="secondary-button" href="/login">Выйти к входу</Link>
        </div>
      </section>

      <section className="grid two-up briefs-grid">
        {steps.map((step) => (
          <article className="card stack-sm" key={step.title}>
            <h2>{step.title}</h2>
            <p className="muted">{step.description}</p>
            <Link className="secondary-button" href={step.href}>{step.label}</Link>
          </article>
        ))}
      </section>

      <section className="card stack-sm">
        <h2>Ролевой гейтинг</h2>
        <p className="muted">
          Менеджеры и владельцы могут создавать/редактировать, reviewer — читать и согласовывать. Этот экран не дублирует правила, а лишь ведёт по ним.
        </p>
        <ul className="stack-xs">
          <li>Owner / manager — создание брендов, товаров, медиа, ЦА и планов.</li>
          <li>Reviewer — review-only режим, без создания новых сущностей.</li>
          <li>Members — управляются через организационные membership-записи.</li>
        </ul>
      </section>
    </main>
  );
}
