import Link from 'next/link';

const steps = [
  {
    title: '1. Открыть dashboard и выбрать organization',
    description: 'Dashboard подтягивает доступные memberships и даёт выбрать рабочий контекст.',
    href: '/dashboard',
    label: 'Dashboard',
  },
  {
    title: '2. Открыть брендовый кабинет и выбрать бренд',
    description: 'После выбора organization на dashboard здесь видно список брендов, карточку выбранного бренда и форму редактирования Brand DNA.',
    href: '/brands',
    label: 'Brands',
  },
  {
    title: '3. Добавить товары и запустить Product DNA',
    description: 'Товарные карточки собирают SKU, описание, преимущества, доказательства и ограничения.',
    href: '/products',
    label: 'Products',
  },
  {
    title: '4. Загрузить медиа и описать ЦА',
    description: 'Медиатека и аудитории дают контекст для контент-планов и материалов.',
    href: '/media-assets',
    label: 'Media',
  },
  {
    title: '5. Открыть production flow и пройти весь маршрут',
    description: 'Production flow показывает следующий шаг, counts по сущностям и прямые ссылки на нужный экран.',
    href: '/production-flow',
    label: 'Flow',
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
