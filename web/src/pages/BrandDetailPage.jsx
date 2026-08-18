import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { brandsAPI } from '../api/client';
import { ArrowLeft, Plus, Trash2, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useToast } from '../components/Toast';
import BrandBootstrap from '../components/BrandBootstrap';

const TABS = [
  { id: 'docs',      label: 'Tài liệu' },
  { id: 'bootstrap', label: 'Nạp liệu' },
  { id: 'voice',     label: 'Giọng điệu' },
  { id: 'settings',  label: 'Thiết lập' },
  { id: 'preview',   label: 'AI thấy gì' },
];

const DOC_CATEGORIES = {
  brand_core: 'Nhận diện & giọng',
  products:   'Sản phẩm',
  audience:   'Đối tượng',
  policies:   'Quy định',
  general:    'Khác',
};

const DOC_TYPE_OPTIONS = [
  { value: 'brand_core', label: 'Nhận diện, giọng điệu', prefix: '' },
  { value: 'products',   label: 'Sản phẩm / dịch vụ',    prefix: 'products/' },
  { value: 'audience',   label: 'Chân dung đối tượng',   prefix: 'audience/' },
  { value: 'policies',   label: 'Quy định nội dung',     prefix: 'policies/' },
];

export default function BrandDetailPage() {
  const { brandId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast, Toast } = useToast();

  const [brand, setBrand] = useState(null);
  // Tab nằm trên URL để gửi link được và để BrandsPage đưa thẳng vào 'bootstrap'
  const urlTab = searchParams.get('tab');
  const [tab, setTab] = useState(
    TABS.some(t => t.id === urlTab) ? urlTab : 'docs'
  );

  const changeTab = (id) => {
    setTab(id);
    setSearchParams(id === 'docs' ? {} : { tab: id }, { replace: true });
  };
  const [loading, setLoading] = useState(true);
  const [showAddDoc, setShowAddDoc] = useState(false);
  const [newDoc, setNewDoc] = useState({ type: 'products', name: '' });

  const [voiceProfile, setVoiceProfile] = useState(null);
  const [voiceDirty, setVoiceDirty] = useState(false);
  const [settings, setSettings] = useState(null);
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { loadBrand(); }, [brandId]);
  useEffect(() => { if (tab === 'voice') loadVoice(); }, [tab]);
  useEffect(() => { if (tab === 'preview') loadPreview(); }, [tab]);

  const loadBrand = async () => {
    try {
      const { data } = await brandsAPI.get(brandId);
      setBrand(data);
      setSettings({
        name: data.name, description: data.description, color: data.color, icon: data.icon,
        default_channels: data.default_channels || [], default_goal: data.default_goal || 'awareness',
        forbidden_claims: data.forbidden_claims || [], mandatory_terms: data.mandatory_terms || [],
      });
    } catch { navigate('/knowledge'); }
    finally { setLoading(false); }
  };

  const loadVoice = async () => {
    try { const { data } = await brandsAPI.getVoice(brandId); setVoiceProfile(data); }
    catch { setVoiceProfile(null); }
  };

  const loadPreview = async () => {
    try { const { data } = await brandsAPI.preview(brandId); setPreview(data); }
    catch { setPreview(null); }
  };

  const saveVoice = async () => {
    setBusy(true);
    try { await brandsAPI.updateVoice(brandId, voiceProfile); setVoiceDirty(false); showToast('Đã lưu giọng điệu.', 'success'); }
    catch (err) { showToast(err.response?.data?.detail?.message || err.message); }
    finally { setBusy(false); }
  };

  const saveSettings = async () => {
    setBusy(true);
    try { await brandsAPI.update(brandId, settings); setSettingsDirty(false); loadBrand(); showToast('Đã lưu thiết lập.', 'success'); }
    catch (err) { showToast(err.response?.data?.detail?.message || err.message); }
    finally { setBusy(false); }
  };

  const addDocument = () => {
    if (!newDoc.name) return;
    const opt = DOC_TYPE_OPTIONS.find(o => o.value === newDoc.type);
    const docPath = opt.prefix + newDoc.name.toLowerCase().replace(/\s+/g, '_') + '.md';
    navigate(`/knowledge/${brandId}/edit/${docPath}`);
  };

  const deleteDoc = async (docPath) => {
    if (!window.confirm(`Xoá tài liệu “${docPath}”?`)) return;
    try { await brandsAPI.deleteDoc(brandId, docPath); loadBrand(); }
    catch (err) { showToast(err.response?.data?.detail?.message || err.message); }
  };

  if (loading) return <p className="text-ink-3 py-12">Đang tải…</p>;
  if (!brand) return null;

  const grouped = {};
  (brand.documents || []).forEach(doc => {
    (grouped[doc.category] = grouped[doc.category] || []).push(doc);
  });

  return (
    <div className="rise">
      <header className="flex items-center gap-3 mb-7">
        <button onClick={() => navigate('/knowledge')} aria-label="Về kho brand" className="btn btn-quiet !p-2">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span
          aria-hidden="true"
          className="w-9 h-9 shrink-0 flex items-center justify-center text-base rounded-[3px]"
          style={{ background: brand.color + '1a', border: `1px solid ${brand.color}55` }}
        >
          {brand.icon}
        </span>
        <div className="min-w-0">
          <h1 className="t-section truncate">{brand.name}</h1>
          <p className="text-[0.8125rem] text-ink-2 truncate">{brand.description || 'Chưa có mô tả'}</p>
        </div>
      </header>

      <div className="scroll-x border-b border-rule mb-7">
        <div className="flex gap-6 min-w-max">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => changeTab(t.id)}
              aria-current={tab === t.id ? 'true' : undefined}
              className={`pb-3 -mb-px border-b-2 text-[0.875rem] transition-colors ${
                tab === t.id ? 'border-cham font-semibold text-ink' : 'border-transparent text-ink-2 hover:border-rule-strong'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ---------------- Tài liệu ---------------- */}
      {tab === 'docs' && (
        <div>
          <div className="flex items-center justify-between gap-3 mb-4">
            <p className="t-label">{brand.documents?.length || 0} tài liệu</p>
            <button onClick={() => setShowAddDoc(true)} className="btn btn-default !py-2 !px-3 !text-[13px]">
              <Plus className="w-3.5 h-3.5" /> Thêm tài liệu
            </button>
          </div>

          {showAddDoc && (
            <div className="sheet p-5 mb-5 rise">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 mb-4">
                <div>
                  <label htmlFor="d-type" className="t-label block mb-2">Loại</label>
                  <select id="d-type" value={newDoc.type}
                          onChange={e => setNewDoc({ ...newDoc, type: e.target.value })} className="field">
                    {DOC_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label htmlFor="d-name" className="t-label block mb-2">Tên file</label>
                  <input id="d-name" value={newDoc.name}
                         onChange={e => setNewDoc({ ...newDoc, name: e.target.value })}
                         placeholder="ca_phe_sua_da" className="field font-data" />
                </div>
              </div>
              <div className="flex gap-2.5">
                <button onClick={addDocument} disabled={!newDoc.name} className="btn btn-primary">
                  Tạo và viết
                </button>
                <button onClick={() => setShowAddDoc(false)} className="btn btn-quiet">Huỷ</button>
              </div>
            </div>
          )}

          {Object.entries(DOC_CATEGORIES).map(([catKey, catLabel]) => {
            const docs = grouped[catKey];
            if (!docs?.length) return null;
            return (
              <section key={catKey} className="mb-6">
                <p className="t-label mb-2.5">{catLabel}</p>
                <div className="sheet">
                  {docs.map((doc, i) => (
                    <div key={doc.path}
                         className={`group lift flex items-center gap-3 px-5 py-3.5 ${i < docs.length - 1 ? 'border-b border-rule' : ''}`}>
                      <button
                        onClick={() => navigate(`/knowledge/${brandId}/edit/${doc.path}`)}
                        className="flex-1 min-w-0 text-left"
                      >
                        <span className="block text-[0.9375rem] truncate">{doc.name}</span>
                        <span className="block t-data num mt-0.5 truncate">
                          {doc.path} · {(doc.size / 1024).toFixed(1)} KB
                        </span>
                      </button>
                      <button
                        onClick={() => deleteDoc(doc.path)}
                        aria-label={`Xoá ${doc.path}`}
                        className="btn btn-quiet !p-2 shrink-0 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                        style={{ color: 'var(--fail)' }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {/* ---------------- Nạp liệu ---------------- */}
      {tab === 'bootstrap' && (
        <BrandBootstrap brandId={brandId} onApplied={loadBrand} showToast={showToast} />
      )}

      {/* ---------------- Giọng điệu ---------------- */}
      {tab === 'voice' && voiceProfile && (
        <div>
          <div className="flex items-center justify-between gap-3 mb-4">
            <p className="t-lede !text-[0.9375rem]">Bộ quy tắc giọng dùng cho mọi nội dung của brand này.</p>
            <button onClick={saveVoice} disabled={!voiceDirty || busy} className="btn btn-primary shrink-0">
              {busy && <Loader2 className="w-4 h-4 animate-spin" />} Lưu
            </button>
          </div>

          <div className="space-y-5">
            <Block title="Tông giọng">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 mb-5">
                <Text label="Tông chính" value={voiceProfile.tone?.primary || ''}
                      onChange={v => { setVoiceProfile({ ...voiceProfile, tone: { ...voiceProfile.tone, primary: v } }); setVoiceDirty(true); }} />
                <Text label="Tông phụ" value={voiceProfile.tone?.secondary || ''}
                      onChange={v => { setVoiceProfile({ ...voiceProfile, tone: { ...voiceProfile.tone, secondary: v } }); setVoiceDirty(true); }} />
              </div>
              <div>
                <div className="flex items-baseline justify-between mb-2">
                  <span className="t-label">Mức trang trọng</span>
                  <span className="t-data num">{(voiceProfile.tone?.formality ?? 0.5).toFixed(1)}</span>
                </div>
                <input
                  type="range" min="0" max="1" step="0.1"
                  value={voiceProfile.tone?.formality ?? 0.5}
                  onChange={e => { setVoiceProfile({ ...voiceProfile, tone: { ...voiceProfile.tone, formality: parseFloat(e.target.value) } }); setVoiceDirty(true); }}
                  className="w-full accent-[var(--cham)]"
                />
                <div className="flex justify-between t-label mt-1">
                  <span>Thân mật</span><span>Trang trọng</span>
                </div>
              </div>
            </Block>

            <Block title="Từ ngữ">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                <Lines label="Từ nên dùng" value={voiceProfile.vocabulary?.preferred || []}
                       onChange={v => { setVoiceProfile({ ...voiceProfile, vocabulary: { ...voiceProfile.vocabulary, preferred: v } }); setVoiceDirty(true); }} />
                <Lines label="Từ cần tránh" value={voiceProfile.vocabulary?.avoided || []}
                       onChange={v => { setVoiceProfile({ ...voiceProfile, vocabulary: { ...voiceProfile.vocabulary, avoided: v } }); setVoiceDirty(true); }} />
              </div>
            </Block>

            <Block title="Chống văn máy" hint="Những mở đầu và cách nói sáo mòn cần tránh. Mỗi dòng một quy tắc.">
              <Lines value={voiceProfile.anti_ai_rules || []} rows={4}
                     placeholder={'Không mở bài bằng "Bạn đã bao giờ"\nTránh "Trong thế giới hiện đại"'}
                     onChange={v => { setVoiceProfile({ ...voiceProfile, anti_ai_rules: v }); setVoiceDirty(true); }} />
            </Block>
          </div>
        </div>
      )}

      {/* ---------------- Thiết lập ---------------- */}
      {tab === 'settings' && settings && (
        <div>
          <div className="flex items-center justify-between gap-3 mb-4">
            <p className="t-lede !text-[0.9375rem]">Thông tin chung và luật cứng khi sinh nội dung.</p>
            <button onClick={saveSettings} disabled={!settingsDirty || busy} className="btn btn-primary shrink-0">
              {busy && <Loader2 className="w-4 h-4 animate-spin" />} Lưu
            </button>
          </div>

          <div className="space-y-5">
            <Block title="Chung">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                <Text label="Tên hiển thị" value={settings.name}
                      onChange={v => { setSettings({ ...settings, name: v }); setSettingsDirty(true); }} />
                <Text label="Mô tả" value={settings.description}
                      onChange={v => { setSettings({ ...settings, description: v }); setSettingsDirty(true); }} />
              </div>
            </Block>

            <Block title="Luật nội dung" hint="Được kiểm tra bằng luật cứng sau khi sinh nội dung, không phụ thuộc vào AI.">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                <Lines label="Không bao giờ được nói" value={settings.forbidden_claims || []}
                       placeholder="cam kết khỏi bệnh 100%"
                       onChange={v => { setSettings({ ...settings, forbidden_claims: v }); setSettingsDirty(true); }} />
                <Lines label="Bắt buộc phải có" value={settings.mandatory_terms || []}
                       placeholder="tên thương hiệu"
                       onChange={v => { setSettings({ ...settings, mandatory_terms: v }); setSettingsDirty(true); }} />
              </div>
            </Block>

            <div className="sheet p-5" style={{ borderLeft: '2px solid var(--fail)' }}>
              <p className="t-label mb-1.5" style={{ color: 'var(--fail)' }}>Xoá brand</p>
              <p className="text-[0.875rem] text-ink-2 mb-4 max-w-[54ch] leading-relaxed">
                Xoá toàn bộ tài liệu, giọng điệu và thiết lập của brand này. Không khôi phục được.
              </p>
              <button
                onClick={async () => {
                  if (!window.confirm(`Xoá hoàn toàn brand “${brand.name}”?`)) return;
                  await brandsAPI.delete(brandId);
                  navigate('/knowledge');
                }}
                className="btn btn-danger"
              >
                Xoá brand này
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- AI thấy gì ---------------- */}
      {tab === 'preview' && (
        <div>
          <p className="t-lede !text-[0.9375rem] mb-5">
            Toàn bộ kiến thức sẽ được nạp vào ngữ cảnh khi sinh nội dung cho brand này.
          </p>

          {preview ? (
            <div className="space-y-4">
              <div className="sheet px-5 py-4 flex items-center justify-between gap-4 flex-wrap">
                <span className="t-data num">
                  {(preview.total_size_bytes / 1024).toFixed(1)} KB · khoảng {preview.estimated_tokens.toLocaleString('vi-VN')} token
                </span>
                <span className={`tag ${preview.context_usage_percent < 10 ? 'tag-pass' : 'tag-warn'}`}>
                  Chiếm {preview.context_usage_percent}% ngữ cảnh
                </span>
              </div>

              {Object.entries(preview.sections || {}).map(([key, value]) => (
                <section key={key} className="sheet px-5 py-4">
                  <p className="t-label mb-3">{key.replace(/_/g, ' ')}</p>
                  {typeof value === 'string' ? (
                    <div className="md !text-[0.9375rem]">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
                    </div>
                  ) : (
                    <pre className="font-data text-[0.75rem] text-ink-2 scroll-x">{JSON.stringify(value, null, 2)}</pre>
                  )}
                </section>
              ))}
            </div>
          ) : (
            <p className="text-ink-3 py-8">Đang tải…</p>
          )}
        </div>
      )}

      <Toast />
    </div>
  );
}

function Block({ title, hint, children }) {
  return (
    <section className="sheet p-5">
      <p className="t-label mb-1">{title}</p>
      {hint && <p className="text-[0.8125rem] text-ink-2 mb-4 max-w-[56ch] leading-relaxed">{hint}</p>}
      <div className={hint ? '' : 'mt-4'}>{children}</div>
    </section>
  );
}

function Text({ label, value, onChange }) {
  return (
    <div>
      <label className="t-label block mb-2">{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)} className="field" />
    </div>
  );
}

function Lines({ label, value, onChange, rows = 5, placeholder }) {
  return (
    <div>
      {label && <label className="t-label block mb-2">{label}</label>}
      <textarea
        value={value.join('\n')}
        onChange={e => onChange(e.target.value.split('\n').filter(Boolean))}
        rows={rows}
        placeholder={placeholder}
        className="field !text-[0.875rem]"
      />
    </div>
  );
}
