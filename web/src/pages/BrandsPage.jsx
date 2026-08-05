import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { brandsAPI } from '../api/client';
import { Plus, Trash2, X } from 'lucide-react';
import { useToast } from '../components/Toast';

const BRAND_ICONS = ['📦', '☕', '💅', '🏠', '🎵', '📱', '🎨', '🍕', '✦', '🌿', '💎', '🔥'];

const CHECK_LABEL = {
  identity: 'Nhận diện',
  tone: 'Giọng điệu',
  product: 'Sản phẩm',
  audience: 'Đối tượng',
};

/* Thanh hoàn thiện: bốn ô, mỗi ô là một loại tài liệu bắt buộc.
   Hình dạng mang thông tin — nhìn ô nào rỗng là biết thiếu gì. */
function Completeness({ completeness }) {
  const { score, checks } = completeness;
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-[3px]">
        {Object.keys(CHECK_LABEL).map(key => (
          <span
            key={key}
            title={`${CHECK_LABEL[key]}: ${checks[key] ? 'đã có' : 'còn thiếu'}`}
            className="w-5 h-[5px]"
            style={{ background: checks[key] ? 'var(--pass)' : 'var(--rule)' }}
          />
        ))}
      </div>
      <span className="t-data num">{score}%</span>
    </div>
  );
}

export default function BrandsPage() {
  const navigate = useNavigate();
  const { showToast, Toast } = useToast();
  const [brands, setBrands] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [newBrand, setNewBrand] = useState({ id: '', name: '', description: '', icon: '📦', color: '#2f3e86' });

  useEffect(() => { loadBrands(); }, []);

  const loadBrands = async () => {
    try {
      const { data } = await brandsAPI.list();
      setBrands(data);
    } catch {
      showToast('Không tải được danh sách brand.');
    } finally {
      setLoading(false);
    }
  };

  const createBrand = async () => {
    if (!newBrand.id || !newBrand.name) return;
    try {
      await brandsAPI.create(newBrand);
      setShowCreate(false);
      setNewBrand({ id: '', name: '', description: '', icon: '📦', color: '#2f3e86' });
      loadBrands();
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    }
  };

  const deleteBrand = async (id, name) => {
    if (!window.confirm(`Xoá brand “${name}” cùng toàn bộ tài liệu?\nKhông khôi phục được.`)) return;
    try {
      await brandsAPI.delete(id);
      loadBrands();
      showToast(`Đã xoá “${name}”.`, 'success');
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="rise">
      <header className="flex items-start justify-between gap-4 flex-wrap mb-8">
        <div>
          <h1 className="t-page !text-[2rem] !font-light mb-2.5">Kho brand</h1>
          <p className="t-lede">
            Mỗi brand có nhận diện, giọng điệu và quy định riêng. Nạp càng đầy, nội dung càng đúng chất.
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn btn-primary shrink-0">
          <Plus className="w-4 h-4" /> Thêm brand
        </button>
      </header>

      {showCreate && (
        <div className="sheet p-6 mb-6 rise relative">
          <button
            onClick={() => setShowCreate(false)}
            aria-label="Đóng"
            className="btn btn-quiet !p-2 absolute top-3 right-3"
          >
            <X className="w-4 h-4" />
          </button>

          <h2 className="t-section mb-5">Brand mới</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5 mb-5">
            <div>
              <label htmlFor="b-id" className="t-label block mb-2">Mã brand</label>
              <input
                id="b-id"
                value={newBrand.id}
                onChange={e => setNewBrand({ ...newBrand, id: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '_') })}
                placeholder="ca_phe_abc"
                className="field font-data"
              />
              <p className="text-[0.8125rem] text-ink-3 mt-1.5">Chữ thường không dấu, dùng gạch dưới. Không đổi được sau khi tạo.</p>
            </div>
            <div>
              <label htmlFor="b-name" className="t-label block mb-2">Tên hiển thị</label>
              <input
                id="b-name"
                value={newBrand.name}
                onChange={e => setNewBrand({ ...newBrand, name: e.target.value })}
                placeholder="Cà Phê ABC"
                className="field"
              />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="b-desc" className="t-label block mb-2">Mô tả ngắn</label>
              <input
                id="b-desc"
                value={newBrand.description}
                onChange={e => setNewBrand({ ...newBrand, description: e.target.value })}
                placeholder="Quán cà phê specialty tại quận 1"
                className="field"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-6 mb-6">
            <div>
              <p className="t-label mb-2">Biểu tượng</p>
              <div className="flex gap-1 flex-wrap max-w-[280px]">
                {BRAND_ICONS.map(icon => (
                  <button
                    key={icon}
                    onClick={() => setNewBrand({ ...newBrand, icon })}
                    aria-pressed={newBrand.icon === icon}
                    className="w-8 h-8 text-base flex items-center justify-center rounded-[3px] border transition-colors"
                    style={{
                      borderColor: newBrand.icon === icon ? 'var(--cham)' : 'var(--rule)',
                      background: newBrand.icon === icon ? 'var(--cham-soft)' : 'transparent',
                    }}
                  >
                    {icon}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="b-color" className="t-label block mb-2">Màu</label>
              <input
                id="b-color"
                type="color"
                value={newBrand.color}
                onChange={e => setNewBrand({ ...newBrand, color: e.target.value })}
                className="w-10 h-10 cursor-pointer border border-rule rounded-[3px] bg-transparent p-0.5"
              />
            </div>
          </div>

          <div className="flex gap-2.5">
            <button onClick={createBrand} disabled={!newBrand.id || !newBrand.name} className="btn btn-primary">
              Tạo brand
            </button>
            <button onClick={() => setShowCreate(false)} className="btn btn-quiet">Huỷ</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-ink-3 py-12">Đang tải…</p>
      ) : brands.length === 0 ? (
        <div className="sheet px-6 py-12 text-center">
          <p className="font-copy text-[1.125rem] mb-1.5">Chưa có brand nào</p>
          <p className="text-[0.9375rem] text-ink-2 max-w-[42ch] mx-auto">
            Không bắt buộc — bạn vẫn chạy được chiến dịch không brand. Thêm brand khi muốn nội dung bám đúng giọng riêng.
          </p>
        </div>
      ) : (
        <div className="sheet spot">
          {brands.map((brand, i) => (
            <div
              key={brand.id}
              className={`group lift flex items-center gap-4 px-5 py-4 ${i < brands.length - 1 ? 'border-b border-rule' : ''}`}
            >
              <button
                onClick={() => navigate(`/knowledge/${brand.id}`)}
                className="flex items-center gap-4 flex-1 min-w-0 text-left"
              >
                <span
                  aria-hidden="true"
                  className="w-9 h-9 shrink-0 flex items-center justify-center text-base rounded-[3px]"
                  style={{ background: brand.color + '1a', border: `1px solid ${brand.color}55` }}
                >
                  {brand.icon}
                </span>
                <span className="min-w-0">
                  <span className="block text-[0.9375rem] font-medium truncate">{brand.name}</span>
                  <span className="block text-[0.8125rem] text-ink-2 truncate">
                    {brand.description || 'Chưa có mô tả'}
                    <span className="text-ink-3"> · {brand.document_count} tài liệu</span>
                  </span>
                  {brand.completeness && (
                    <span className="block mt-1.5"><Completeness completeness={brand.completeness} /></span>
                  )}
                </span>
              </button>

              <button
                onClick={() => deleteBrand(brand.id, brand.name)}
                aria-label={`Xoá brand ${brand.name}`}
                className="btn btn-quiet !p-2 shrink-0 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                style={{ color: 'var(--fail)' }}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Gợi ý lấp khoảng trống khi kho còn ít brand — nói việc cần làm tiếp */}
      {!loading && brands.length > 0 && (
        <p className="mt-6 text-[0.875rem] text-ink-3 max-w-[56ch] leading-relaxed">
          Bấm vào một brand để bổ sung tài liệu. Bốn ô trên thanh hoàn thiện là nhận diện,
          giọng điệu, sản phẩm và đối tượng — ô nào còn xám là phần AI chưa có gì để dựa vào.
        </p>
      )}

      <Toast />
    </div>
  );
}
