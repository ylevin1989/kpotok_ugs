'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { loadSession, loadScopeSelection } from '../../lib/auth';
import { listContentItems, listContentItemImages, generateContentItemImage, fetchMediaBlobUrl, type StudioContentItem } from '../../lib/api';

export default function StudioPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [items, setItems] = useState<StudioContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [images, setImages] = useState<Record<string, string>>({});
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [noScope, setNoScope] = useState(false);

  useEffect(() => {
    const s = loadSession();
    if (!s) { router.push('/login'); return; }
    setToken(s.accessToken);
    const scope = loadScopeSelection();
    if (!scope?.organizationId || !scope?.brandId) { setNoScope(true); setLoading(false); return; }
    listContentItems(s.accessToken, scope.organizationId, scope.brandId)
      .then(async (r) => {
        setItems(r.items);
        // load already-generated images for each post
        await Promise.all(r.items.map(async (it) => {
          try {
            const imgs = await listContentItemImages(s.accessToken, it.id);
            const latest = imgs.items[0];
            if (latest) {
              const url = await fetchMediaBlobUrl(s.accessToken, latest.file_url);
              setImages((m) => ({ ...m, [it.id]: url }));
              if (latest.image_prompt) setPrompts((m) => ({ ...m, [it.id]: latest.image_prompt }));
            }
          } catch {
            /* ignore per-item image load errors */
          }
        }));
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [router]);

  async function genImage(item: StudioContentItem) {
    if (!token) return;
    setBusy((b) => ({ ...b, [item.id]: true }));
    setErr(null);
    try {
      const res = await generateContentItemImage(token, item.id);
      const url = await fetchMediaBlobUrl(token, res.file_url);
      setImages((m) => ({ ...m, [item.id]: url }));
      setPrompts((m) => ({ ...m, [item.id]: res.image_prompt }));
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy((b) => ({ ...b, [item.id]: false }));
    }
  }

  if (noScope) {
    return (
      <div className="card">
        <h2>Выбери бренд</h2>
        <p className="muted">Наверху выбери организацию и бренд — студия работает в рамках выбранного бренда.</p>
      </div>
    );
  }

  return (
    <div className="stack-lg">
      <div className="stack-xs">
        <span className="eyebrow">Медиа</span>
        <h1>Медиа-студия</h1>
        <p className="muted">Готовые посты бренда. Под каждый пост можно сгенерировать изображение (арт-директор строит промпт из текста поста и генерит картинку через kie.ai).</p>
      </div>

      {err && <div className="error-card">{err}</div>}

      {loading ? (
        <p className="muted">Загрузка…</p>
      ) : items.length === 0 ? (
        <div className="empty">У этого бренда пока нет постов. Сгенерируй материалы из контент-плана, затем возвращайся сюда за картинками.</div>
      ) : (
        <div className="grid two-up">
          {items.map((item) => (
            <div key={item.id} className="card stack-md">
              <div className="section-header">
                <div className="stack-xs">
                  <h2 style={{ fontSize: '1rem' }}>{item.title}</h2>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span className="pill">{item.platform}</span>
                    <span className="subtle-pill">{item.content_type}</span>
                    <span className={item.status === 'approved' ? 'badge ok' : item.status === 'internal_review' ? 'badge warn' : 'badge info'}>{item.status}</span>
                    {item.quality_score > 0 && <span className="subtle-pill">QS {item.quality_score}</span>}
                  </div>
                </div>
              </div>

              {images[item.id] ? (
                <img src={images[item.id]} alt={item.title} style={{ width: '100%', borderRadius: 12, border: '1px solid var(--border)' }} />
              ) : (
                <div className="empty" style={{ padding: '28px 16px' }}>Изображение ещё не сгенерировано</div>
              )}

              {prompts[item.id] && (
                <details>
                  <summary className="muted" style={{ cursor: 'pointer', fontSize: '0.85rem' }}>Промпт изображения</summary>
                  <p className="faint" style={{ fontSize: '0.82rem', marginTop: 6 }}>{prompts[item.id]}</p>
                </details>
              )}

              <button className="primary-button" style={{ width: 'fit-content' }} disabled={!!busy[item.id]} onClick={() => genImage(item)}>
                {busy[item.id] ? 'Генерируем… (~40 сек)' : images[item.id] ? 'Сгенерировать заново' : 'Сгенерировать картинку'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
