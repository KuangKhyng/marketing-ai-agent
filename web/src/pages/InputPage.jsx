import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { campaignAPI, brandsAPI, templatesAPI } from '../api/client';
import { Loader2, Sparkles, Wand2, BookmarkPlus, FolderOpen } from 'lucide-react';
import { useToast } from '../components/Toast';

export default function InputPage({ setCampaignData, setPhase, loading, setLoading }) {
  const navigate = useNavigate();
  const { showToast, Toast } = useToast();
  const [mode, setMode] = useState('structured');
  const [freeText, setFreeText] = useState('');
  const [brands, setBrands] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [language, setLanguage] = useState('vi');
  const [templates, setTemplates] = useState([]);
  const [showTemplates, setShowTemplates] = useState(false);
  const [form, setForm] = useState({
    goal: 'awareness',
    product: '',
    audience: '',
    channels: ['facebook', 'instagram'],
    key_message: '',
    cta: '',
  });

  useEffect(() => {
    brandsAPI.list().then(res => setBrands(res.data)).catch(() => {});
    templatesAPI.list().then(res => setTemplates(res.data)).catch(() => {});
  }, []);

  const handleLoadTemplate = async (templateId) => {
    try {
      const { data } = await templatesAPI.get(templateId);
      const brief = data.brief || {};
      setMode('structured');
      setForm({
        goal: brief.goal || 'awareness',
        product: brief.offer?.product_or_service || '',
        audience: brief.audience?.persona_description || '',
        channels: brief.channels || ['facebook', 'instagram'],
        key_message: brief.offer?.key_message || '',
        cta: brief.offer?.cta || '',
      });
      if (brief.brand?.voice_profile_id && brief.brand.voice_profile_id !== 'default') {
        setSelectedBrand(brief.brand.voice_profile_id);
      }
      setShowTemplates(false);
      showToast(`Đã load template: ${data.name}`, 'success');
    } catch {
      showToast('Lỗi khi load template.');
    }
  };

  const handleSaveTemplate = async () => {
    const name = prompt('Tên template:');
    if (!name) return;
    try {
      await templatesAPI.create({
        name,
        description: `${form.goal} - ${form.product}`,
        brief: {
          goal: form.goal,
          brand: { name: '', voice_profile_id: selectedBrand || 'default' },
          audience: { persona_description: form.audience },
          offer: { product_or_service: form.product, key_message: form.key_message, cta: form.cta },
          channels: form.channels,
        },
      });
      const { data } = await templatesAPI.list();
      setTemplates(data);
      showToast(`Đã lưu template "${name}"!`, 'success');
    } catch {
      showToast('Lỗi khi lưu template.');
    }
  };

  const handleSubmit = async () => {
    // Validate structured mode
    if (mode === 'structured') {
      if (!form.product.trim() && !form.key_message.trim()) {
        showToast('Vui lòng nhập ít nhất Sản phẩm hoặc Thông điệp cốt lõi.');
        return;
      }
      if (form.channels.length === 0) {
        showToast('Vui lòng chọn ít nhất 1 mạng xã hội.');
        return;
      }
    }

    setLoading(true);
    try {
      const input = mode === 'free_text'
        ? { mode: 'free_text', raw_input: freeText, brand_id: selectedBrand, language }
        : { mode: 'structured', ...form, brand_id: selectedBrand, language };

      const { data } = await campaignAPI.start(input);
      setCampaignData(data);
      setPhase('brief_review');
    } catch (err) {
      showToast('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-6 md:mb-8">
        <h2 className="text-3xl md:text-4xl font-bold mb-2 md:mb-3 tracking-tight">Campaign Builder</h2>
        <p className="text-base md:text-lg opacity-70">
          Mô tả ý tưởng của bạn, AI sẽ lo phần còn lại.
        </p>
      </div>

      <div className="glass-panel p-5 md:p-8 rounded-2xl w-full max-w-full overflow-hidden">
        {/* Template Selector */}
        {templates.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium opacity-80 flex items-center gap-1">
                <FolderOpen className="w-3 h-3" /> Templates
              </label>
              <button onClick={() => setShowTemplates(!showTemplates)}
                      className="text-xs text-purple-400 hover:text-purple-300 cursor-pointer">
                {showTemplates ? 'Hide' : `${templates.length} saved`}
              </button>
            </div>
            {showTemplates && (
              <div className="flex gap-2 flex-wrap animate-in fade-in duration-300">
                {templates.map(t => (
                  <button key={t.id} onClick={() => handleLoadTemplate(t.id)}
                          className="px-4 py-2.5 rounded-xl text-sm font-medium bg-[#252540]/60 text-gray-300 border border-white/5 hover:border-purple-500/50 hover:bg-purple-500/10 transition-all cursor-pointer flex items-center gap-2">
                    📌 {t.name}
                    <span className="text-xs opacity-40">{t.brief_summary}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Brand Selector */}
        {brands.length > 0 && (
          <div className="mb-6">
            <label className="text-xs font-medium mb-2 block opacity-80">Brand Knowledge</label>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => setSelectedBrand(null)}
                      className={`px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all cursor-pointer ${
                        !selectedBrand
                          ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg'
                          : 'bg-[#252540]/60 text-gray-400 border border-white/5 hover:border-purple-500/50'
                      }`}>
                🌐 Generic (không brand)
              </button>
              {brands.map(brand => (
                <button key={brand.id}
                        onClick={() => setSelectedBrand(brand.id)}
                        className={`px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all cursor-pointer ${
                          selectedBrand === brand.id
                            ? 'text-white shadow-lg'
                            : 'bg-[#252540]/60 text-gray-400 border border-white/5 hover:border-purple-500/50'
                        }`}
                        style={selectedBrand === brand.id ? { backgroundColor: brand.color } : {}}>
                  {brand.icon} {brand.name}
                </button>
              ))}
              <button onClick={() => navigate('/knowledge')}
                      className="px-4 py-2.5 rounded-xl text-sm flex items-center gap-1 cursor-pointer"
                      style={{ color: 'var(--text-muted)', border: '1px dashed var(--border)' }}>
                + Thêm brand
              </button>
            </div>
          </div>
        )}

        {/* Language selector */}
        <div className="mb-6">
          <label className="text-xs font-medium mb-2 block opacity-80">Ngôn ngữ Content</label>
          <div className="flex gap-2">
            {[{id: 'vi', label: '🇻🇳 Tiếng Việt'}, {id: 'en', label: '🇺🇸 English'}].map(lang => (
              <button key={lang.id} onClick={() => setLanguage(lang.id)}
                      className={`px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all cursor-pointer ${
                        language === lang.id
                          ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg'
                          : 'bg-[#252540]/60 text-gray-400 border border-white/5 hover:border-purple-500/50'
                      }`}>
                {lang.label}
              </button>
            ))}
          </div>
        </div>

        {/* Mode toggle */}
        <div className="flex flex-col md:flex-row gap-2 mb-6 md:mb-8 bg-[#1a1a2e]/50 p-1.5 rounded-xl border border-white/5 md:inline-flex backdrop-blur-md w-full md:w-auto">
          {['free_text', 'structured'].map(m => (
            <button key={m} onClick={() => setMode(m)}
                    className={`px-4 md:px-6 py-2.5 rounded-lg text-sm md:text-base font-medium transition-all cursor-pointer flex-1 text-center ${
                      mode === m 
                        ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/25' 
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}>
              {m === 'free_text' ? 'Mô tả Tự do' : 'Biểu mẫu rập khuôn'}
            </button>
          ))}
        </div>

        {mode === 'free_text' ? (
          <div>
            <label className="text-sm md:text-base font-medium mb-2 opacity-80 flex items-center gap-2">
              <Wand2 className="w-4 h-4 text-purple-400 shrink-0" /> Nhập Prompt
            </label>
            <textarea value={freeText} onChange={e => setFreeText(e.target.value)}
                      placeholder="Ví dụ: Tạo campaign awareness cho dịch vụ học tiếng Anh online, target Gen Z yêu thích phát triển bản thân..."
                      rows={6}
                      className="w-full p-4 md:p-5 rounded-xl text-sm md:text-base glass-input resize-y placeholder:opacity-40"
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 md:gap-6">
            {/* Goal */}
            <div>
              <label className="text-sm font-medium mb-2 block opacity-80">Mục tiêu</label>
              <select value={form.goal} onChange={e => setForm({...form, goal: e.target.value})}
                      className="w-full p-4 rounded-xl text-sm glass-input text-white [&>option]:bg-[#1a1a2e]">
                <option value="awareness">Awareness (Nhận diện)</option>
                <option value="engagement">Engagement (Tương tác)</option>
                <option value="lead_generation">Lead Generation (Khách hàng tiềm năng)</option>
                <option value="conversion">Conversion (Chuyển đổi mua hàng)</option>
              </select>
            </div>

            {/* Channels */}
            <div>
              <label className="text-sm font-medium mb-2 block opacity-80">Mạng xã hội</label>
              <div className="flex flex-wrap gap-2">
                {['facebook', 'instagram', 'tiktok'].map(ch => (
                  <button key={ch} onClick={() => {
                    const channels = form.channels.includes(ch)
                      ? form.channels.filter(c => c !== ch)
                      : [...form.channels, ch];
                    setForm({...form, channels});
                  }}
                  className={`px-3 md:px-4 py-2.5 md:py-2.5 rounded-xl text-xs font-semibold capitalize transition-all cursor-pointer ${
                    form.channels.includes(ch) 
                      ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-md' 
                      : 'bg-[#252540]/60 text-gray-400 border border-white/5 hover:border-purple-500/50'
                  }`}>
                    {ch}
                  </button>
                ))}
              </div>
            </div>

            <InputField label="Sản phẩm / Dịch vụ" value={form.product}
                        onChange={v => setForm({...form, product: v})}
                        placeholder="VD: Ứng dụng học tiếng Anh giao tiếp" />

            <InputField label="Thông điệp cốt lõi" value={form.key_message}
                        onChange={v => setForm({...form, key_message: v})}
                        placeholder="VD: Nói tiếng Anh tự tin trong 90 ngày" />

            <InputField label="Audience (Đối tượng)" value={form.audience}
                        onChange={v => setForm({...form, audience: v})}
                        placeholder="VD: Gen Z, 18-25 tuổi, muốn cải thiện ngoại ngữ..." />

            <InputField label="Call to Action (CTA)" value={form.cta}
                        onChange={v => setForm({...form, cta: v})}
                        placeholder="VD: Đăng ký học thử miễn phí" />
          </div>
        )}

        {/* Generate button */}
        <div className="flex gap-3 mt-10">
          <button onClick={handleSubmit} disabled={loading || (mode==='free_text' && !freeText)}
                  className="flex-1 py-4 rounded-xl text-base font-bold flex items-center justify-center gap-2 btn-primary group">
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> Đang thiết lập Campaign...</>
            ) : (
              <><Sparkles className="w-5 h-5 group-hover:animate-pulse text-yellow-300" /> Bắt đầu Generate AI</>
            )}
          </button>
          {mode === 'structured' && (
            <button onClick={handleSaveTemplate} disabled={loading || (!form.product.trim() && !form.key_message.trim())}
                    className="px-5 py-4 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 btn-secondary disabled:opacity-30"
                    title="Lưu form hiện tại làm template">
              <BookmarkPlus className="w-5 h-5" />
              <span className="hidden md:inline">Lưu Template</span>
            </button>
          )}
        </div>
      </div>
      <Toast />
    </div>
  );
}

function InputField({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="text-sm font-medium mb-2 block opacity-80">{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
             className="w-full p-4 rounded-xl text-sm glass-input placeholder:opacity-40" />
    </div>
  );
}
