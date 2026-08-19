import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { brandsAPI } from '../api/client';
import { ArrowLeft, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useToast } from '../components/Toast';

const TEMPLATES = {
  identity: `# [Tên brand]

## Brand là gì
(Brand làm gì, cho ai, vì sao tồn tại)

## Sứ mệnh
(1–2 câu)

## Điểm khác biệt
(Điều gì khiến brand khác với đối thủ)

## Giá trị cốt lõi
- (Giá trị 1)
- (Giá trị 2)

## Tính cách brand
(Nếu brand là một người thì đó là người thế nào)
`,
  tone_of_voice: `# Giọng điệu

## Tổng thể
(Thân mật / trang trọng / gần gũi / dứt khoát…)

## Nên
- (Nên viết kiểu gì)

## Không nên
- (Tránh viết kiểu gì)

## Từ ngữ ưa dùng
- (Từ 1)

## Emoji
(Nhiều / vừa / ít / không dùng)

## Bài mẫu tốt
(Dán 3–5 bài đã đăng và thấy hiệu quả)
`,
  products: `# [Tên sản phẩm hoặc dịch vụ]

## Mô tả ngắn
(1–2 câu)

## Chi tiết
(Mô tả đầy đủ)

## Dành cho ai
(Ai nên dùng)

## Lợi ích chính
- (Lợi ích 1)
- (Lợi ích 2)

## Giá
(Nếu có)
`,
  audience: `# Chân dung: [Tên nhóm]

## Nhân khẩu
- Tuổi:
- Giới tính:
- Khu vực:
- Nghề nghiệp:

## Nỗi đau
- (Nỗi đau 1)
- (Nỗi đau 2)

## Động lực
- (Động lực 1)

## Cách họ nói chuyện
(Ngôn ngữ, từ lóng, cách xưng hô)

## Họ ở đâu
(Nền tảng nào, nhóm nào)
`,
  policies: `# [Tên quy định]

## Quy định
- (Quy định 1)

## Được phép nói
- (Claim 1)

## Không được nói
- (Claim cấm 1)
`,
};

function getTemplate(docPath) {
  if (docPath.startsWith('products/')) return TEMPLATES.products;
  if (docPath.startsWith('audience/')) return TEMPLATES.audience;
  if (docPath.startsWith('policies/')) return TEMPLATES.policies;
  if (docPath.includes('identity')) return TEMPLATES.identity;
  if (docPath.includes('tone')) return TEMPLATES.tone_of_voice;
  return '# Tài liệu\n\n(Viết nội dung tại đây)\n';
}

export default function DocumentEditorPage() {
  const { brandId, '*': docPath } = useParams();
  const navigate = useNavigate();
  const { showToast, Toast } = useToast();
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isNew, setIsNew] = useState(false);

  // Lưu nháp vào máy mỗi 30s để mất mạng không mất bài
  useEffect(() => {
    const key = `draft_${brandId}_${docPath}`;
    const interval = setInterval(() => {
      if (content && content !== originalContent) localStorage.setItem(key, content);
    }, 30000);
    return () => clearInterval(interval);
  }, [content, originalContent, brandId, docPath]);

  const loadDocument = useCallback(async () => {
    try {
      const { data } = await brandsAPI.getDoc(brandId, docPath);
      setContent(data.content);
      setOriginalContent(data.content);
      setIsNew(false);
    } catch {
      const draft = localStorage.getItem(`draft_${brandId}_${docPath}`);
      setContent(draft || getTemplate(docPath));
      setOriginalContent('');
      setIsNew(true);
    } finally {
      setLoading(false);
    }
  }, [brandId, docPath]);

  // Đặt sau khai báo loadDocument: mảng deps được tính lúc render nên tham
  // chiếu tới const chưa khởi tạo sẽ ném ReferenceError.
  useEffect(() => { loadDocument(); }, [loadDocument]);

  const saveDocument = async () => {
    setSaving(true);
    try {
      await brandsAPI.saveDoc(brandId, docPath, content);
      setOriginalContent(content);
      setIsNew(false);
      localStorage.removeItem(`draft_${brandId}_${docPath}`);
      showToast('Đã lưu.', 'success');
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  const isDirty = content !== originalContent;
  const docName = docPath.split('/').pop().replace('.md', '').replace(/_/g, ' ');

  if (loading) return <p className="text-ink-3 py-12">Đang tải…</p>;

  return (
    <div className="rise">
      <header className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div className="flex items-start gap-3 min-w-0">
          <button
            onClick={() => navigate(`/knowledge/${brandId}`)}
            aria-label="Quay lại brand"
            className="btn btn-quiet !p-2 mt-0.5"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="min-w-0">
            <h1 className="t-section capitalize truncate">{docName}</h1>
            <p className="t-data mt-1 truncate">
              {docPath}
              {isNew && <span className="text-ink-3"> · tài liệu mới</span>}
              {isDirty && <span style={{ color: 'var(--warn)' }}> · chưa lưu</span>}
            </p>
          </div>
        </div>
        <div className="flex gap-2.5 shrink-0">
          <button onClick={saveDocument} disabled={saving || !isDirty} className="btn btn-primary">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {saving ? 'Đang lưu' : 'Lưu'}
          </button>
          <button onClick={() => navigate(`/knowledge/${brandId}`)} className="btn btn-quiet">Đóng</button>
        </div>
      </header>

      {isNew && (
        <p className="text-[0.875rem] text-ink-2 leading-relaxed mb-5 sheet px-4 py-3"
           style={{ borderLeft: '2px solid var(--cham)' }}>
          Đã điền sẵn dàn ý. Thay các phần trong ngoặc bằng thông tin thật — phần nào chưa có thì xoá dòng đó đi,
          để trống còn hơn để chữ mẫu lọt vào nội dung.
        </p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="flex flex-col">
          <p className="t-label mb-2">Soạn thảo</p>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            spellCheck={false}
            className="field font-data !text-[0.8125rem] !leading-[1.7] flex-1"
            style={{ minHeight: '460px' }}
          />
        </div>
        <div className="flex flex-col">
          <p className="t-label mb-2">Bản đọc</p>
          <div className="inset px-5 py-4 overflow-auto flex-1" style={{ minHeight: '460px' }}>
            <div className="md !text-[0.9375rem]">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          </div>
        </div>
      </div>

      <Toast />
    </div>
  );
}
