import type { ReactNode } from 'react';
import './globals.css';
import Chrome from '../components/Chrome';

export const metadata = {
  title: 'Контент-завод',
  description: 'AI Content Ops платформа',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <div className="app-shell">
          <Chrome>{children}</Chrome>
        </div>
      </body>
    </html>
  );
}
