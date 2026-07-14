'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { loadSession, loadScopeSelection } from '../../lib/auth';
import { getProducts, listReferences, uploadReference, deleteReference, fetchMediaBlobUrl, type ReferenceAsset } from '../../lib/api';
import type { ProductRead } from '../../lib/types';

export default function ReferencesPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [scope, setScope] = useState<{ org: string; brand: string } | null>(null);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [productId, setProductId] = useState<string>(''); // '' = brand-level
  const [refs, setRefs] = useState<ReferenceAsset[]>([]);
  const [thumbs, setThumbs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [noScope, setNoScope] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const s = loadSession();
    if (!s) { router.push('/login'); return; }
    setToken(s.accessToken);
    const sc = loadScopeSelection();
    if (!sc?.organizationId || !sc?.brandId) { setNoScope(true); setLoading(false); return; }
    setScope({ org: sc.organizationId, brand: sc.brandId });
    getProducts(s.accessToken, sc.organizationId, sc.brandId).then((r) => setProducts(r.items)).catch(() => {});
  }, [router]);

  async function loadRefs(tok: string, org: string, brand: string, pid: string) {
    setLoading(true);
    try {
      const r = await listReferences(tok, org, brand, pid || undefined);
      setRefs(r.items);
      const map: Record<string, string> = {};
      await Promise.all(r.items.map(async (a) => {
        try { map[a.id] = await fetchMediaBlobUrl(tok, a.file_url); } catch { /* skip */ }
      }));
      setThumbs(map);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token && scope) loadRefs(token, scope.org, scope.brand, productId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, scope, productId]);

  async function onFiles(files: FileList | null) {
    if (!token || !scope || !files || files.length === 0) return;
    setUploading(true); setErr(null);
    try {
      for (const file of Array.from(files)) {
        await uploadReference(token, { organizationId: scope.org, brandId: scope.brand, productId: productId || null, file });
      }
      await loadRefs(token, scope.org, scope.brand, productId);
    } catch (e) {
      setErr(String(e));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function onDelete(id: string) {
    if (!token) return;
    try {
      await deleteReference(token, id);
      setRefs((r) => r.filter((x) => x.id !== id));
    } catch (e) {
      setErr(String(e));
    }
  }

  if (noScope) {
    return <div className="card"><h2>Выбери бренд</h2><p className="muted">Наверху выбери организацию и бренд.</p></div>;
  }

  return (
    <div className="stack-lg">
      <div className="stack-xs">
        <span className="eyebrow">Медиа</span>
        <h1>Референсы</h1>
        <p className="muted">Загрузи 10–15 фото реального продукта (или бренда). Их использует генератор картинок: изображения к постам будут повторять твой продукт (image-to-image через kie.ai).</p>
      </div>

      {err && <div className="error-card">{err}</div>}

      <div className="card stack-md">
        <div className="grid two-up">
          <label className="label-stack">
            <span>К чему привязать референсы</span>
            <select className="input" value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">Весь бренд</option>
              {products.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
            </select>
          </label>
          <div className="label-stack">
            <span>Загрузить изображения (можно несколько)</span>
            <input ref={fileRef} className="input" type="file" accept="image/*" multiple disabled={uploading} onChange={(e) => onFiles(e.target.files)} />
          </div>
        </div>
        {uploading && <p className="muted">Загрузка…</p>}
        <p className="faint" style={{ fontSize: '0.82rem' }}>
          {productId ? 'Референсы товара используются при генерации картинок к его постам.' : 'Референсы бренда — общие; для точного повторения товара привязывай к конкретному товару.'}
        </p>
      </div>

      <div className="card stack-md">
        <div className="section-header"><h2>Загруженные референсы ({refs.length})</h2></div>
        {loading ? (
          <p className="muted">Загрузка…</p>
        ) : refs.length === 0 ? (
          <div className="empty">Пока нет референсов. Загрузи фото продукта выше.</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 14 }}>
            {refs.map((a) => (
              <div key={a.id} className="subtle-card" style={{ padding: 8, position: 'relative' }}>
                {thumbs[a.id] ? (
                  <img src={thumbs[a.id]} alt={a.name} style={{ width: '100%', height: 140, objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }} />
                ) : (
                  <div className="empty" style={{ height: 140, padding: 0, display: 'grid', placeItems: 'center' }}>…</div>
                )}
                <div className="faint" style={{ fontSize: '0.72rem', marginTop: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name}</div>
                <button className="secondary-button" style={{ minHeight: 28, padding: '2px 8px', fontSize: '0.78rem', marginTop: 6, width: '100%' }} onClick={() => onDelete(a.id)}>Удалить</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
