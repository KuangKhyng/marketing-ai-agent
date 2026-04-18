import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { brandsAPI } from '../api/client';
import { Plus, Trash2, FolderOpen, X } from 'lucide-react';

const BRAND_ICONS = ['📦', '☕', '💅', '🏠', '🎵', '📱', '🎨', '🍕', '✦', '🌿', '💎', '🔥'];

function CompletenessBar({ completeness }) {
  const { score, checks } = completeness;
  const segments = [
    { key: 'identity', label: 'Identity', filled: checks.identity },
    { key: 'tone', label: 'Tone', filled: checks.tone },
    { key: 'product', label: 'Product', filled: checks.product },
    { key: 'audience', label: 'Audience', filled: checks.audience },
  ];

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {segments.map(s => (
          <div key={s.key} className="w-5 h-2 rounded-sm transition-colors" title={s.label}
               style={{ backgroundColor: s.filled ? 'var(--success)' : 'rgba(255,255,255,0.1)' }} />
        ))}
      </div>
      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{score}%</span>
    </div>
  );
}

export default function BrandsPage() {
  const navigate = useNavigate();
  const [brands, setBrands] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [newBrand, setNewBrand] = useState({ id: '', name: '', description: '', icon: '📦', color: '#6c5ce7' });

  useEffect(() => { loadBrands(); }, []);

  const loadBrands = async () => {
    try {
      const { data } = await brandsAPI.list();
      setBrands(data);
    } catch (err) {
      console.error('Failed to load brands:', err);
    } finally {
      setLoading(false);
    }
  };

  const createBrand = async () => {
    if (!newBrand.id || !newBrand.name) return;
    try {
      await brandsAPI.create(newBrand);
      setShowCreate(false);
      setNewBrand({ id: '', name: '', description: '', icon: '📦', color: '#6c5ce7' });
      loadBrands();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    }
  };

  const deleteBrand = async (id, name) => {
    if (!confirm(`Xóa brand "${name}" và tất cả knowledge?\nKhông thể hoàn tác!`)) return;
    try {
      await brandsAPI.delete(id);
      loadBrands();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h2 className="text-3xl md:text-4xl font-bold mb-2 tracking-tight">📚 Knowledge Base</h2>
          <p className="text-base opacity-70">Quản lý brand knowledge cho campaigns</p>
        </div>
        <button onClick={() => setShowCreate(true)}
                className="px-5 py-3 rounded-xl text-sm font-semibold flex items-center gap-2 btn-primary">
          <Plus className="w-4 h-4" /> Tạo Brand Mới
        </button>
      </div>

      {/* Create Brand Form */}
      {showCreate && (
        <div className="glass-panel rounded-2xl p-6 mb-6 relative">
          <button onClick={() => setShowCreate(false)} className="absolute top-4 right-4 p-1 rounded-lg hover:bg-white/10">
            <X className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          </button>
          <h3 className="text-lg font-semibold mb-5">Tạo Brand Mới</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>
                Brand ID (lowercase, không dấu, dùng _)
              </label>
              <input value={newBrand.id}
                     onChange={e => setNewBrand({...newBrand, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_')})}
                     placeholder="coffee_shop_abc"
                     className="w-full p-3 rounded-xl text-sm glass-input" />
            </div>
            <div>
              <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Tên hiển thị</label>
              <input value={newBrand.name}
                     onChange={e => setNewBrand({...newBrand, name: e.target.value})}
                     placeholder="Coffee Shop ABC"
                     className="w-full p-3 rounded-xl text-sm glass-input" />
            </div>
          </div>
          <div className="mb-4">
            <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Mô tả</label>
            <input value={newBrand.description}
                   onChange={e => setNewBrand({...newBrand, description: e.target.value})}
                   placeholder="Quán cà phê specialty tại quận 1"
                   className="w-full p-3 rounded-xl text-sm glass-input" />
          </div>
          <div className="flex items-center gap-4 mb-5">
            <div>
              <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Icon</label>
              <div className="flex gap-1 flex-wrap">
                {BRAND_ICONS.map(icon => (
                  <button key={icon} onClick={() => setNewBrand({...newBrand, icon})}
                          className={`w-9 h-9 rounded-lg text-base flex items-center justify-center transition-all ${
                            newBrand.icon === icon ? 'ring-2 ring-purple-500 bg-white/10' : 'hover:bg-white/5'
                          }`}>
                    {icon}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Màu chủ đạo</label>
              <input type="color" value={newBrand.color}
                     onChange={e => setNewBrand({...newBrand, color: e.target.value})}
                     className="w-10 h-10 rounded-lg cursor-pointer border-0 bg-transparent" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={createBrand} disabled={!newBrand.id || !newBrand.name}
                    className="px-5 py-2.5 rounded-xl text-sm font-semibold btn-primary disabled:opacity-50">
              ✅ Tạo Brand
            </button>
            <button onClick={() => setShowCreate(false)}
                    className="px-5 py-2.5 rounded-xl text-sm btn-secondary">
              Hủy
            </button>
          </div>
        </div>
      )}

      {/* Brand List */}
      {loading ? (
        <div className="text-center py-20 opacity-50">Đang tải...</div>
      ) : brands.length === 0 ? (
        <div className="glass-panel rounded-2xl text-center py-16">
          <p className="text-5xl mb-4">📚</p>
          <p className="text-lg font-medium mb-2">Chưa có brand nào</p>
          <p className="text-sm opacity-60">Bấm "Tạo Brand Mới" để bắt đầu thêm knowledge cho brand đầu tiên</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {brands.map(brand => (
            <div key={brand.id}
                 className="glass-panel rounded-2xl p-5 flex items-center justify-between transition-all hover:brightness-110 cursor-pointer group"
                 onClick={() => navigate(`/knowledge/${brand.id}`)}>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center text-xl"
                     style={{ backgroundColor: brand.color + '20', color: brand.color }}>
                  {brand.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-base">{brand.name}</h3>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    {brand.description} · {brand.document_count} documents
                  </p>
                  {brand.completeness && <div className="mt-1.5"><CompletenessBar completeness={brand.completeness} /></div>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4 opacity-0 group-hover:opacity-50 transition-opacity" />
                <button onClick={e => { e.stopPropagation(); deleteBrand(brand.id, brand.name); }}
                        className="p-2 rounded-lg hover:bg-red-500/20 transition-colors opacity-0 group-hover:opacity-100"
                        style={{ color: 'var(--error)' }}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
