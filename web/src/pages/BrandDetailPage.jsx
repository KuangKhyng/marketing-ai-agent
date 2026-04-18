import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { brandsAPI } from '../api/client';
import { ArrowLeft, Plus, Trash2, Edit3, Save, X, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const TABS = [
  { id: 'docs', label: '📄 Documents', icon: '📄' },
  { id: 'voice', label: '🎤 Voice', icon: '🎤' },
  { id: 'settings', label: '⚙️ Settings', icon: '⚙️' },
  { id: 'preview', label: '👁 Preview', icon: '👁' },
];

const DOC_CATEGORIES = {
  brand_core: { label: 'BRAND CORE', icon: '📝', color: '#8b5cf6' },
  products: { label: 'PRODUCTS', icon: '📦', color: '#f59e0b' },
  audience: { label: 'AUDIENCE', icon: '👥', color: '#10b981' },
  policies: { label: 'POLICIES', icon: '🛡️', color: '#ef4444' },
  general: { label: 'OTHER', icon: '📄', color: '#6b7280' },
};

const DOC_TYPE_OPTIONS = [
  { value: 'brand_core', label: '📝 Brand Core (identity, tone...)', prefix: '' },
  { value: 'products', label: '📦 Product / Dịch vụ', prefix: 'products/' },
  { value: 'audience', label: '👥 Audience / Persona', prefix: 'audience/' },
  { value: 'policies', label: '🛡️ Policy / Quy định', prefix: 'policies/' },
];

export default function BrandDetailPage() {
  const { brandId } = useParams();
  const navigate = useNavigate();
  const [brand, setBrand] = useState(null);
  const [tab, setTab] = useState('docs');
  const [loading, setLoading] = useState(true);
  const [showAddDoc, setShowAddDoc] = useState(false);
  const [newDoc, setNewDoc] = useState({ type: 'products', name: '' });

  // Voice profile state
  const [voiceProfile, setVoiceProfile] = useState(null);
  const [voiceDirty, setVoiceDirty] = useState(false);

  // Settings state
  const [settings, setSettings] = useState(null);
  const [settingsDirty, setSettingsDirty] = useState(false);

  // Preview state
  const [preview, setPreview] = useState(null);

  useEffect(() => { loadBrand(); }, [brandId]);
  useEffect(() => { if (tab === 'voice') loadVoice(); }, [tab]);
  useEffect(() => { if (tab === 'preview') loadPreview(); }, [tab]);

  const loadBrand = async () => {
    try {
      const { data } = await brandsAPI.get(brandId);
      setBrand(data);
      setSettings({ name: data.name, description: data.description, color: data.color, icon: data.icon,
                     default_channels: data.default_channels || [], default_goal: data.default_goal || 'awareness',
                     forbidden_claims: data.forbidden_claims || [], mandatory_terms: data.mandatory_terms || [] });
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
    await brandsAPI.updateVoice(brandId, voiceProfile);
    setVoiceDirty(false);
  };

  const saveSettings = async () => {
    await brandsAPI.update(brandId, settings);
    setSettingsDirty(false);
    loadBrand();
  };

  const addDocument = async () => {
    if (!newDoc.name) return;
    const opt = DOC_TYPE_OPTIONS.find(o => o.value === newDoc.type);
    const docPath = opt.prefix + newDoc.name.toLowerCase().replace(/\s+/g, '_') + '.md';
    navigate(`/knowledge/${brandId}/edit/${docPath}`);
  };

  const deleteDoc = async (docPath) => {
    if (!confirm(`Xóa document "${docPath}"?`)) return;
    await brandsAPI.deleteDoc(brandId, docPath);
    loadBrand();
  };

  if (loading) return <div className="text-center py-20 opacity-50">Đang tải...</div>;
  if (!brand) return null;

  // Group documents by category
  const grouped = {};
  (brand.documents || []).forEach(doc => {
    const cat = doc.category;
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(doc);
  });

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/knowledge')} className="p-2 rounded-lg hover:bg-white/10 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
             style={{ backgroundColor: brand.color + '20', color: brand.color }}>
          {brand.icon}
        </div>
        <div>
          <h2 className="text-2xl font-bold">{brand.name}</h2>
          <p className="text-xs opacity-60">{brand.description}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-[#1a1a2e]/50 p-1 rounded-xl border border-white/5 overflow-x-auto">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
                  className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                    tab === t.id
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'docs' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">📄 Documents</h3>
            <button onClick={() => setShowAddDoc(true)} className="px-4 py-2 rounded-xl text-sm font-medium btn-primary flex items-center gap-2">
              <Plus className="w-4 h-4" /> Thêm Document
            </button>
          </div>

          {showAddDoc && (
            <div className="glass-panel rounded-xl p-5 mb-4">
              <h4 className="text-sm font-semibold mb-3">Thêm Document Mới</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Loại</label>
                  <select value={newDoc.type} onChange={e => setNewDoc({...newDoc, type: e.target.value})}
                          className="w-full p-3 rounded-xl text-sm glass-input text-white [&>option]:bg-[#1a1a2e]">
                    {DOC_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Tên (không dấu)</label>
                  <input value={newDoc.name} onChange={e => setNewDoc({...newDoc, name: e.target.value})}
                         placeholder="ten_document" className="w-full p-3 rounded-xl text-sm glass-input" />
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={addDocument} disabled={!newDoc.name} className="px-4 py-2 rounded-xl text-sm font-medium btn-primary disabled:opacity-50">
                  → Tạo & Bắt đầu viết
                </button>
                <button onClick={() => setShowAddDoc(false)} className="px-4 py-2 rounded-xl text-sm btn-secondary">Hủy</button>
              </div>
            </div>
          )}

          {Object.entries(DOC_CATEGORIES).map(([catKey, catInfo]) => {
            const docs = grouped[catKey];
            if (!docs || docs.length === 0) return null;
            return (
              <div key={catKey} className="mb-5">
                <h4 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: catInfo.color }}>
                  {catInfo.icon} {catInfo.label}
                </h4>
                <div className="space-y-2">
                  {docs.map(doc => (
                    <div key={doc.path} className="glass-panel rounded-xl p-4 flex items-center justify-between group hover:brightness-110 transition-all">
                      <div className="flex items-center gap-3 cursor-pointer flex-1"
                           onClick={() => navigate(`/knowledge/${brandId}/edit/${doc.path}`)}>
                        <span className="text-base">{catInfo.icon}</span>
                        <div>
                          <p className="text-sm font-medium">{doc.name}</p>
                          <p className="text-xs opacity-50">{doc.path} · {(doc.size / 1024).toFixed(1)} KB</p>
                        </div>
                      </div>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => navigate(`/knowledge/${brandId}/edit/${doc.path}`)}
                                className="p-2 rounded-lg hover:bg-white/10" title="Sửa">
                          <Edit3 className="w-4 h-4 text-purple-400" />
                        </button>
                        <button onClick={() => deleteDoc(doc.path)}
                                className="p-2 rounded-lg hover:bg-red-500/20" title="Xóa">
                          <Trash2 className="w-4 h-4" style={{ color: 'var(--error)' }} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === 'voice' && voiceProfile && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">🎤 Voice Profile</h3>
            <button onClick={saveVoice} disabled={!voiceDirty} className="px-4 py-2 rounded-xl text-sm font-medium btn-primary disabled:opacity-50 flex items-center gap-2">
              <Save className="w-4 h-4" /> Lưu
            </button>
          </div>
          <div className="space-y-5">
            {/* Tone */}
            <div className="glass-panel rounded-xl p-5">
              <h4 className="text-sm font-bold uppercase tracking-wider mb-3 text-purple-400">Tone</h4>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Primary Tone</label>
                  <input value={voiceProfile.tone?.primary || ''} onChange={e => { setVoiceProfile({...voiceProfile, tone: {...voiceProfile.tone, primary: e.target.value}}); setVoiceDirty(true); }}
                         className="w-full p-3 rounded-xl text-sm glass-input" />
                </div>
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Secondary Tone</label>
                  <input value={voiceProfile.tone?.secondary || ''} onChange={e => { setVoiceProfile({...voiceProfile, tone: {...voiceProfile.tone, secondary: e.target.value}}); setVoiceDirty(true); }}
                         className="w-full p-3 rounded-xl text-sm glass-input" />
                </div>
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Formality: {voiceProfile.tone?.formality ?? 0.5}</label>
                <input type="range" min="0" max="1" step="0.1" value={voiceProfile.tone?.formality ?? 0.5}
                       onChange={e => { setVoiceProfile({...voiceProfile, tone: {...voiceProfile.tone, formality: parseFloat(e.target.value)}}); setVoiceDirty(true); }}
                       className="w-full accent-purple-500" />
                <div className="flex justify-between text-xs opacity-50"><span>Casual</span><span>Formal</span></div>
              </div>
            </div>
            {/* Vocabulary */}
            <div className="glass-panel rounded-xl p-5">
              <h4 className="text-sm font-bold uppercase tracking-wider mb-3 text-green-400">Vocabulary</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Preferred words (1 per line)</label>
                  <textarea value={(voiceProfile.vocabulary?.preferred || []).join('\n')}
                            onChange={e => { setVoiceProfile({...voiceProfile, vocabulary: {...voiceProfile.vocabulary, preferred: e.target.value.split('\n').filter(Boolean)}}); setVoiceDirty(true); }}
                            rows={5} className="w-full p-3 rounded-xl text-sm glass-input resize-y" />
                </div>
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Avoided words (1 per line)</label>
                  <textarea value={(voiceProfile.vocabulary?.avoided || []).join('\n')}
                            onChange={e => { setVoiceProfile({...voiceProfile, vocabulary: {...voiceProfile.vocabulary, avoided: e.target.value.split('\n').filter(Boolean)}}); setVoiceDirty(true); }}
                            rows={5} className="w-full p-3 rounded-xl text-sm glass-input resize-y" />
                </div>
              </div>
            </div>
            {/* Anti-AI Rules */}
            <div className="glass-panel rounded-xl p-5">
              <h4 className="text-sm font-bold uppercase tracking-wider mb-3 text-yellow-400">Anti-AI Rules</h4>
              <textarea value={(voiceProfile.anti_ai_rules || []).join('\n')}
                        onChange={e => { setVoiceProfile({...voiceProfile, anti_ai_rules: e.target.value.split('\n').filter(Boolean)}); setVoiceDirty(true); }}
                        rows={4} className="w-full p-3 rounded-xl text-sm glass-input resize-y"
                        placeholder="Mỗi dòng 1 rule..." />
            </div>
          </div>
        </div>
      )}

      {tab === 'settings' && settings && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">⚙️ Brand Settings</h3>
            <button onClick={saveSettings} disabled={!settingsDirty} className="px-4 py-2 rounded-xl text-sm font-medium btn-primary disabled:opacity-50 flex items-center gap-2">
              <Save className="w-4 h-4" /> Lưu
            </button>
          </div>
          <div className="space-y-5">
            <div className="glass-panel rounded-xl p-5">
              <h4 className="text-sm font-bold uppercase tracking-wider mb-3 text-purple-400">General</h4>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Tên hiển thị</label>
                  <input value={settings.name} onChange={e => { setSettings({...settings, name: e.target.value}); setSettingsDirty(true); }}
                         className="w-full p-3 rounded-xl text-sm glass-input" />
                </div>
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Mô tả</label>
                  <input value={settings.description} onChange={e => { setSettings({...settings, description: e.target.value}); setSettingsDirty(true); }}
                         className="w-full p-3 rounded-xl text-sm glass-input" />
                </div>
              </div>
            </div>
            <div className="glass-panel rounded-xl p-5">
              <h4 className="text-sm font-bold uppercase tracking-wider mb-3 text-red-400">Content Rules</h4>
              <div className="mb-4">
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Forbidden claims (1 per line)</label>
                <textarea value={(settings.forbidden_claims || []).join('\n')}
                          onChange={e => { setSettings({...settings, forbidden_claims: e.target.value.split('\n').filter(Boolean)}); setSettingsDirty(true); }}
                          rows={3} className="w-full p-3 rounded-xl text-sm glass-input resize-y"
                          placeholder="AI sẽ KHÔNG BAO GIỜ nói những điều này..." />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Mandatory terms (1 per line)</label>
                <textarea value={(settings.mandatory_terms || []).join('\n')}
                          onChange={e => { setSettings({...settings, mandatory_terms: e.target.value.split('\n').filter(Boolean)}); setSettingsDirty(true); }}
                          rows={3} className="w-full p-3 rounded-xl text-sm glass-input resize-y"
                          placeholder="PHẢI xuất hiện trong mọi content..." />
              </div>
            </div>
            {/* Danger Zone */}
            <div className="rounded-xl p-5" style={{ border: '1px solid var(--error)', backgroundColor: 'rgba(239,68,68,0.05)' }}>
              <h4 className="text-sm font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--error)' }}>🗑️ Danger Zone</h4>
              <p className="text-xs opacity-60 mb-3">Xóa toàn bộ knowledge của brand. Không thể hoàn tác.</p>
              <button onClick={async () => {
                if (!confirm(`XÓA HOÀN TOÀN brand "${brand.name}"?`)) return;
                await brandsAPI.delete(brandId);
                navigate('/knowledge');
              }} className="px-4 py-2 rounded-xl text-sm font-medium" style={{ backgroundColor: 'var(--error)', color: '#fff' }}>
                Xóa Brand
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === 'preview' && (
        <div>
          <h3 className="text-lg font-semibold mb-1">👁 Knowledge Preview</h3>
          <p className="text-xs opacity-60 mb-4">Đây là tất cả thông tin AI sẽ dùng khi tạo content cho brand này</p>
          {preview ? (
            <div className="space-y-3">
              {Object.entries(preview.sections || {}).map(([key, value]) => (
                <div key={key} className="glass-panel rounded-xl p-5">
                  <h4 className="text-sm font-bold uppercase tracking-wider mb-2 text-purple-400">{key.replace(/_/g, ' ')}</h4>
                  {typeof value === 'string' ? (
                    <div className="prose prose-invert prose-sm max-w-none text-sm opacity-80">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
                    </div>
                  ) : (
                    <pre className="text-xs opacity-70 overflow-auto">{JSON.stringify(value, null, 2)}</pre>
                  )}
                </div>
              ))}
              <div className="glass-panel rounded-xl p-4 flex items-center justify-between text-sm">
                <span>Total knowledge size: {(preview.total_size_bytes / 1024).toFixed(1)} KB (~{preview.estimated_tokens.toLocaleString()} tokens)</span>
                <span className={preview.context_usage_percent < 10 ? 'text-green-400' : 'text-yellow-400'}>
                  Context usage: {preview.context_usage_percent}% {preview.context_usage_percent < 10 ? '✓ Tốt' : '⚠️ Cần tối ưu'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-10 opacity-50">Đang tải preview...</div>
          )}
        </div>
      )}
    </div>
  );
}
