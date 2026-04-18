import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Loader2, Sparkles, Wand2 } from 'lucide-react';

export default function InputPage({ setCampaignData, setPhase, loading, setLoading }) {
  const [mode, setMode] = useState('structured');
  const [freeText, setFreeText] = useState('');
  const [form, setForm] = useState({
    goal: 'awareness',
    product: '',
    audience: '',
    channels: ['facebook', 'instagram'],
    key_message: '',
    cta: '',
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const input = mode === 'free_text'
        ? { mode: 'free_text', raw_input: freeText }
        : { mode: 'structured', ...form };

      const { data } = await campaignAPI.start(input);
      setCampaignData(data);
      setPhase('brief_review');
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-8">
        <h2 className="text-4xl font-bold mb-3 tracking-tight">Campaign Builder</h2>
        <p className="text-lg opacity-70">
          Mô tả ý tưởng của bạn, AI sẽ lo phần còn lại.
        </p>
      </div>

      <div className="glass-panel p-8 rounded-2xl">
        {/* Mode toggle */}
        <div className="flex gap-2 mb-8 bg-[#1a1a2e]/50 p-1.5 rounded-xl border border-white/5 inline-flex backdrop-blur-md">
          {['free_text', 'structured'].map(m => (
            <button key={m} onClick={() => setMode(m)}
                    className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                      mode === m 
                        ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/25' 
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}>
              {m === 'free_text' ? 'Mô tả Tự do (Free Text)' : 'Biểu mẫu (Structured)'}
            </button>
          ))}
        </div>

        {mode === 'free_text' ? (
          <div>
            <label className="text-sm font-medium mb-2 block opacity-80 flex items-center gap-2">
              <Wand2 className="w-4 h-4 text-purple-400" /> Nhập Prompt
            </label>
            <textarea value={freeText} onChange={e => setFreeText(e.target.value)}
                      placeholder="Ví dụ: Tạo campaign awareness cho dịch vụ tử vi online, target Gen Z quan tâm tâm linh..."
                      rows={6}
                      className="w-full p-5 rounded-xl text-md glass-input resize-y placeholder:opacity-40"
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
              <div className="flex gap-2">
                {['facebook', 'instagram', 'tiktok'].map(ch => (
                  <button key={ch} onClick={() => {
                    const channels = form.channels.includes(ch)
                      ? form.channels.filter(c => c !== ch)
                      : [...form.channels, ch];
                    setForm({...form, channels});
                  }}
                  className={`px-4 py-2.5 rounded-xl text-xs font-semibold capitalize transition-all cursor-pointer ${
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
                        placeholder="VD: Dịch vụ xem lá số tử vi online" />

            <InputField label="Thông điệp cốt lõi" value={form.key_message}
                        onChange={v => setForm({...form, key_message: v})}
                        placeholder="VD: Khám phá bản thân qua các vì sao" />

            <InputField label="Audience (Đối tượng)" value={form.audience}
                        onChange={v => setForm({...form, audience: v})}
                        placeholder="VD: Gen Z, 18-25 tuổi, thích tarot..." />

            <InputField label="Call to Action (CTA)" value={form.cta}
                        onChange={v => setForm({...form, cta: v})}
                        placeholder="VD: Inbox ngay để đặt lịch" />
          </div>
        )}

        {/* Generate button */}
        <button onClick={handleSubmit} disabled={loading || (mode==='free_text' && !freeText)}
                className="w-full mt-10 py-4 rounded-xl text-base font-bold flex items-center justify-center gap-2 btn-primary group">
          {loading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Đang thiết lập Campaign...</>
          ) : (
            <><Sparkles className="w-5 h-5 group-hover:animate-pulse text-yellow-300" /> Bắt đầu Generate AI</>
          )}
        </button>
      </div>
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
