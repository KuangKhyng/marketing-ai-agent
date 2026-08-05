import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { campaignAPI, brandsAPI, templatesAPI } from '../api/client';
import { Loader2, X } from 'lucide-react';
import { useToast } from '../components/Toast';

const GOALS = [
  { v: 'awareness',       l: 'Nhận diện' },
  { v: 'engagement',      l: 'Tương tác' },
  { v: 'lead_generation', l: 'Thu khách tiềm năng' },
  { v: 'conversion',      l: 'Chuyển đổi mua hàng' },
];

const CHANNELS = [
  { v: 'facebook',  l: 'Facebook' },
  { v: 'instagram', l: 'Instagram' },
  { v: 'tiktok',    l: 'TikTok' },
];

export default function InputPage({ setCampaignData, setPhase, loading, setLoading }) {
  const navigate = useNavigate();
  const { showToast, Toast } = useToast();
  const [mode, setMode] = useState('structured');
  const [freeText, setFreeText] = useState('');
  const [brands, setBrands] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [language, setLanguage] = useState('vi');
  const [templates, setTemplates] = useState([]);
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
      showToast(`Đã nạp mẫu “${data.name}”.`, 'success');
    } catch {
      showToast('Không nạp được mẫu.');
    }
  };

  const handleSaveTemplate = async () => {
    const name = prompt('Đặt tên cho mẫu này:');
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
      showToast(`Đã lưu mẫu “${name}”.`, 'success');
    } catch {
      showToast('Không lưu được mẫu.');
    }
  };

  const handleDeleteTemplate = async (templateId, name) => {
    if (!window.confirm(`Xoá mẫu “${name}”?`)) return;
    try {
      await templatesAPI.delete(templateId);
      const { data } = await templatesAPI.list();
      setTemplates(data);
      showToast(`Đã xoá mẫu “${name}”.`, 'success');
    } catch {
      showToast('Không xoá được mẫu.');
    }
  };

  const handleSubmit = async () => {
    if (mode === 'structured') {
      if (!form.product.trim() && !form.key_message.trim()) {
        showToast('Cần ít nhất sản phẩm hoặc thông điệp cốt lõi.');
        return;
      }
      if (form.channels.length === 0) {
        showToast('Chọn ít nhất một kênh.');
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
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleChannel = (ch) => {
    const channels = form.channels.includes(ch)
      ? form.channels.filter(c => c !== ch)
      : [...form.channels, ch];
    setForm({ ...form, channels });
  };

  return (
    <div className="rise">
      <header className="mb-9">
        <h1 className="t-page mb-2.5">Đề bài chiến dịch</h1>
        <p className="t-lede">
          Mô tả điều bạn muốn nói và nói với ai. Phần còn lại sẽ được dựng ra để bạn duyệt từng bước.
        </p>
      </header>

      {/* Brand */}
      {brands.length > 0 && (
        <section className="mb-8">
          <p className="t-label mb-2.5">Brand</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedBrand(null)}
              data-on={!selectedBrand}
              className="chip"
            >
              Không dùng brand
            </button>
            {brands.map(brand => (
              <button
                key={brand.id}
                onClick={() => setSelectedBrand(brand.id)}
                data-on={selectedBrand === brand.id}
                className="chip inline-flex items-center gap-2"
              >
                <span
                  aria-hidden="true"
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ background: brand.color }}
                />
                {brand.name}
              </button>
            ))}
            <button onClick={() => navigate('/knowledge')} className="btn btn-quiet !py-2 !px-3 !text-[13px]">
              Quản lý brand
            </button>
          </div>
          <p className="mt-2 text-[0.8125rem] text-ink-3 leading-snug">
            Chọn brand để AI dùng đúng giọng, sản phẩm và quy định riêng của brand đó.
          </p>
        </section>
      )}

      {/* Mẫu đã lưu */}
      {templates.length > 0 && (
        <section className="mb-8">
          <p className="t-label mb-2.5">Mẫu đã lưu</p>
          <div className="flex flex-wrap gap-2">
            {templates.map(t => (
              <span key={t.id} className="inline-flex items-stretch">
                <button onClick={() => handleLoadTemplate(t.id)} className="chip !rounded-r-none">
                  {t.name}
                  <span className="ml-2 text-ink-3 font-normal">{t.brief_summary}</span>
                </button>
                <button
                  onClick={() => handleDeleteTemplate(t.id, t.name)}
                  aria-label={`Xoá mẫu ${t.name}`}
                  className="chip !rounded-l-none !border-l-0 !px-2"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Cách nhập */}
      <section className="mb-8">
        <p className="t-label mb-2.5">Cách nhập</p>
        <div className="inline-flex border border-rule-strong rounded-[3px] overflow-hidden">
          {[
            { v: 'structured', l: 'Điền biểu mẫu' },
            { v: 'free_text',  l: 'Viết tự do' },
          ].map((m, i) => (
            <button
              key={m.v}
              onClick={() => setMode(m.v)}
              className={`px-4 py-2.5 text-[0.875rem] transition-colors ${i > 0 ? 'border-l border-rule-strong' : ''} ${
                mode === m.v
                  ? 'bg-cham text-on-cham font-semibold'
                  : 'bg-sheet text-ink-2 hover:bg-inset'
              }`}
            >
              {m.l}
            </button>
          ))}
        </div>
      </section>

      {/* Nội dung nhập */}
      {mode === 'free_text' ? (
        <section className="mb-8">
          <label htmlFor="freetext" className="t-label block mb-2">Mô tả chiến dịch</label>
          <textarea
            id="freetext"
            value={freeText}
            onChange={e => setFreeText(e.target.value)}
            rows={7}
            className="field font-copy !text-[1.0625rem]"
            placeholder="Ví dụ: chiến dịch nhận diện cho lớp học tiếng Anh giao tiếp online, hướng tới người đi làm 25–32 tuổi ngại nói trước đám đông…"
          />
        </section>
      ) : (
        <section className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
          <div>
            <label htmlFor="goal" className="t-label block mb-2">Mục tiêu</label>
            <select
              id="goal"
              value={form.goal}
              onChange={e => setForm({ ...form, goal: e.target.value })}
              className="field"
            >
              {GOALS.map(g => <option key={g.v} value={g.v}>{g.l}</option>)}
            </select>
          </div>

          <div>
            <p className="t-label mb-2">Kênh đăng</p>
            <div className="flex flex-wrap gap-2">
              {CHANNELS.map(ch => (
                <button
                  key={ch.v}
                  onClick={() => toggleChannel(ch.v)}
                  data-on={form.channels.includes(ch.v)}
                  className="chip"
                >
                  {ch.l}
                </button>
              ))}
            </div>
          </div>

          <Field
            id="product" label="Sản phẩm hoặc dịch vụ" value={form.product}
            onChange={v => setForm({ ...form, product: v })}
            placeholder="Ứng dụng học tiếng Anh giao tiếp"
          />
          <Field
            id="key_message" label="Thông điệp cốt lõi" value={form.key_message}
            onChange={v => setForm({ ...form, key_message: v })}
            placeholder="Nói tiếng Anh tự tin trong 90 ngày"
          />
          <Field
            id="audience" label="Đối tượng" value={form.audience}
            onChange={v => setForm({ ...form, audience: v })}
            placeholder="Người đi làm 25–32 tuổi, ngại nói trước đám đông"
          />
          <Field
            id="cta" label="Lời kêu gọi hành động" value={form.cta}
            onChange={v => setForm({ ...form, cta: v })}
            placeholder="Đăng ký học thử miễn phí"
          />
        </section>
      )}

      {/* Ngôn ngữ */}
      <section className="mb-9">
        <p className="t-label mb-2.5">Ngôn ngữ nội dung</p>
        <div className="flex gap-2">
          {[{ v: 'vi', l: 'Tiếng Việt' }, { v: 'en', l: 'English' }].map(l => (
            <button key={l.v} onClick={() => setLanguage(l.v)} data-on={language === l.v} className="chip">
              {l.l}
            </button>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap gap-2.5 pt-6 border-t border-rule">
        <button
          onClick={handleSubmit}
          disabled={loading || (mode === 'free_text' && !freeText.trim())}
          className="btn btn-primary"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {loading ? 'Đang dựng brief' : 'Dựng brief'}
        </button>
        {mode === 'structured' && (
          <button
            onClick={handleSaveTemplate}
            disabled={loading || (!form.product.trim() && !form.key_message.trim())}
            className="btn btn-default"
          >
            Lưu thành mẫu
          </button>
        )}
      </div>

      <Toast />
    </div>
  );
}

function Field({ id, label, value, onChange, placeholder }) {
  return (
    <div>
      <label htmlFor={id} className="t-label block mb-2">{label}</label>
      <input
        id={id}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="field"
      />
    </div>
  );
}
