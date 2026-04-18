import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Check, Edit, Loader2 } from 'lucide-react';

export default function BriefReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const brief = campaignData?.brief;
  const [editMode, setEditMode] = useState(false);
  const [editedBrief, setEditedBrief] = useState(brief ? {
    goal: brief.goal,
    product: brief.offer.product_or_service,
    audience: brief.audience.persona_description,
    channels: brief.channels,
    key_message: brief.offer.key_message,
    cta: brief.offer.cta,
  } : {});

  if (!brief) return null;

  const handleApprove = async () => {
    setLoading(true);
    try {
      const { data } = await campaignAPI.approveBrief(campaignData.run_id, editMode ? editedBrief : null);
      setCampaignData(data);
      setPhase('strategy_review');
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-4xl font-bold mb-3 tracking-tight">Parsed Brief</h2>
          <p className="text-lg opacity-70">
            AI đã phân tích yêu cầu của bạn. Hãy kiểm tra lại trước khi tạo chiến lược.
          </p>
        </div>
      </div>

      {/* Brief Display */}
      {!editMode ? (
        <div className="glass-panel p-8 rounded-2xl mb-8 grid grid-cols-1 md:grid-cols-2 gap-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5">
             <Check className="w-64 h-64" />
          </div>
          <div className="relative z-10">
            <p className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">Mục tiêu</p>
            <p className="text-lg font-medium mb-6">{brief.goal}</p>

            <p className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">Sản phẩm / Dịch vụ</p>
            <p className="text-lg font-medium mb-6">{brief.offer.product_or_service}</p>

            <p className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">Đối tượng (Audience)</p>
            <p className="text-lg font-medium">{brief.audience.persona_description}</p>
          </div>
          <div className="relative z-10">
            <p className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">Channels</p>
            <div className="flex gap-2 mb-6">
              {brief.channels.map(c => (
                <span key={c} className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg bg-gradient-to-r from-purple-500/20 to-indigo-500/20 border border-purple-500/30 text-purple-200">{c}</span>
              ))}
            </div>

            <p className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">Key Message</p>
            <p className="text-lg font-medium mb-6">{brief.offer.key_message}</p>

            <p className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">CTA</p>
            <p className="text-lg font-medium text-green-400">{brief.offer.cta}</p>
          </div>
        </div>
      ) : (
        <div className="glass-panel p-8 rounded-2xl mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="col-span-1 md:col-span-2 flex items-center gap-2 text-sm text-yellow-400 bg-yellow-400/10 p-3 rounded-lg border border-yellow-400/20">
              <Edit className="w-4 h-4" /> Editing mode enabled
            </div>
             {/* Goal */}
             <div>
              <label className="text-sm font-medium mb-2 block opacity-80">Mục tiêu</label>
              <select value={editedBrief.goal} onChange={e => setEditedBrief({...editedBrief, goal: e.target.value})}
                      className="w-full p-4 rounded-xl text-sm glass-input text-white [&>option]:bg-[#1a1a2e]">
                <option value="awareness">Awareness</option>
                <option value="engagement">Engagement</option>
                <option value="lead_generation">Lead Generation</option>
                <option value="conversion">Conversion</option>
              </select>
            </div>

            {/* Channels */}
            <div>
              <label className="text-sm font-medium mb-2 block opacity-80">Channels</label>
              <div className="flex gap-2">
                {['facebook', 'instagram', 'tiktok'].map(ch => (
                  <button key={ch} onClick={() => {
                    const channels = editedBrief.channels.includes(ch)
                      ? editedBrief.channels.filter(c => c !== ch)
                      : [...editedBrief.channels, ch];
                    setEditedBrief({...editedBrief, channels});
                  }}
                  className={`px-4 py-2.5 rounded-xl text-xs font-semibold capitalize transition-all cursor-pointer ${
                    editedBrief.channels.includes(ch) 
                      ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-md' 
                      : 'bg-[#252540]/60 text-gray-400 border border-white/5'
                  }`}>
                    {ch}
                  </button>
                ))}
              </div>
            </div>

            <InputField label="Sản phẩm/Dịch vụ" value={editedBrief.product} onChange={v => setEditedBrief({...editedBrief, product: v})} />
            <InputField label="Thông điệp chính" value={editedBrief.key_message} onChange={v => setEditedBrief({...editedBrief, key_message: v})} />
            <InputField label="Đối tượng" value={editedBrief.audience} onChange={v => setEditedBrief({...editedBrief, audience: v})} />
            <InputField label="CTA" value={editedBrief.cta} onChange={v => setEditedBrief({...editedBrief, cta: v})} />
          </div>
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-4">
        <button onClick={() => setEditMode(!editMode)} disabled={loading}
                className="px-8 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer btn-secondary">
          <Edit className="w-5 h-5" />
          {editMode ? 'Hủy Sửa' : 'Sửa Brief'}
        </button>
        <button onClick={handleApprove} disabled={loading}
                className="flex-1 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
          Approve — Tạo Strategy
        </button>
      </div>
    </div>
  );
}

function InputField({ label, value, onChange }) {
  return (
    <div>
      <label className="text-sm font-medium mb-2 block opacity-80">{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)}
             className="w-full p-4 rounded-xl text-sm glass-input" />
    </div>
  );
}
