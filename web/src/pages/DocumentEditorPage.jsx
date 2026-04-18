import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { brandsAPI } from '../api/client';
import { ArrowLeft, Save, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const TEMPLATES = {
  'identity': `# [Tên Brand]

## Brand Identity
(Mô tả brand — brand là gì, làm gì, tại sao tồn tại)

## Mission
(Sứ mệnh — 1-2 câu)

## Vision
(Tầm nhìn)

## Unique Selling Proposition (USP)
(Điều gì khiến brand khác biệt)

## Brand Values
- (Giá trị 1)
- (Giá trị 2)
- (Giá trị 3)

## Brand Personality
(Brand giống ai? Đặc điểm tính cách)
`,
  'tone_of_voice': `# Tone of Voice

## Overall Tone
(casual/formal/friendly/authoritative/...)

## Do's
- (Nên viết kiểu gì)

## Don'ts
- (Không viết kiểu gì)

## Preferred Words/Phrases
- (Từ ưa thích)

## Emoji Usage
(Nhiều/vừa/ít/không dùng)

## Example Posts (Good)
(Paste 3-5 bài post mẫu)
`,
  'products': `# [Tên sản phẩm/dịch vụ]

## Mô tả ngắn
(1-2 câu)

## Chi tiết
(Mô tả đầy đủ)

## Đối tượng
(Ai nên dùng)

## Lợi ích chính
- (Lợi ích 1)
- (Lợi ích 2)

## Giá
(Thông tin giá nếu có)
`,
  'audience': `# Persona: [Tên persona]

## Demographics
- Tuổi: 
- Giới tính:
- Vị trí:
- Nghề nghiệp:

## Pain Points
- (Pain point 1)
- (Pain point 2)

## Motivations
- (Motivation 1)

## Language Style
(Họ nói chuyện như thế nào?)

## Where They Hang Out
(Platform nào? Group nào?)
`,
  'policies': `# [Tên policy]

## Quy định
- (Quy định 1)
- (Quy định 2)

## Claims được phép
- (Claim 1)

## Claims KHÔNG được phép
- (Claim cấm 1)
`,
};

function getTemplate(docPath) {
  if (docPath.startsWith('products/')) return TEMPLATES.products;
  if (docPath.startsWith('audience/')) return TEMPLATES.audience;
  if (docPath.startsWith('policies/')) return TEMPLATES.policies;
  if (docPath.includes('identity')) return TEMPLATES.identity;
  if (docPath.includes('tone')) return TEMPLATES.tone_of_voice;
  return '# Document\n\n(Viết nội dung tại đây)\n';
}

export default function DocumentEditorPage() {
  const { brandId, '*': docPath } = useParams();
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    loadDocument();
  }, [brandId, docPath]);

  // Auto-save draft to localStorage every 30s
  useEffect(() => {
    const key = `draft_${brandId}_${docPath}`;
    const interval = setInterval(() => {
      if (content && content !== originalContent) {
        localStorage.setItem(key, content);
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [content, originalContent, brandId, docPath]);

  const loadDocument = async () => {
    try {
      const { data } = await brandsAPI.getDoc(brandId, docPath);
      setContent(data.content);
      setOriginalContent(data.content);
      setIsNew(false);
    } catch {
      // New document — check for draft or use template
      const draftKey = `draft_${brandId}_${docPath}`;
      const draft = localStorage.getItem(draftKey);
      const template = draft || getTemplate(docPath);
      setContent(template);
      setOriginalContent('');
      setIsNew(true);
    } finally {
      setLoading(false);
    }
  };

  const saveDocument = async () => {
    setSaving(true);
    try {
      await brandsAPI.saveDoc(brandId, docPath, content);
      setOriginalContent(content);
      setIsNew(false);
      // Clear draft
      localStorage.removeItem(`draft_${brandId}_${docPath}`);
    } catch (err) {
      alert('Lỗi khi lưu: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const isDirty = content !== originalContent;
  const docName = docPath.split('/').pop().replace('.md', '').replace(/_/g, ' ');

  if (loading) return <div className="text-center py-20 opacity-50">Đang tải...</div>;

  return (
    <div className="animate-in fade-in duration-500 h-full flex flex-col" style={{ minHeight: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(`/knowledge/${brandId}`)} className="p-2 rounded-lg hover:bg-white/10 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-lg font-bold capitalize">
              {isNew ? '📝 New: ' : '📝 Editing: '}{docName}
            </h2>
            <p className="text-xs opacity-50">{docPath} {isDirty && <span className="text-yellow-400">· Unsaved changes</span>}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={saveDocument} disabled={saving || !isDirty}
                  className="px-4 py-2 rounded-xl text-sm font-medium btn-primary disabled:opacity-50 flex items-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Đang lưu...' : 'Lưu'}
          </button>
          <button onClick={() => navigate(`/knowledge/${brandId}`)}
                  className="px-4 py-2 rounded-xl text-sm btn-secondary">
            Đóng
          </button>
        </div>
      </div>

      {/* Split Editor */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Editor */}
        <div className="flex flex-col">
          <label className="text-xs font-bold uppercase tracking-wider mb-2 text-purple-400">Editor</label>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            className="flex-1 p-4 rounded-xl text-sm glass-input resize-none font-mono leading-relaxed"
            style={{ minHeight: '400px' }}
            spellCheck={false}
          />
        </div>
        {/* Preview */}
        <div className="flex flex-col">
          <label className="text-xs font-bold uppercase tracking-wider mb-2 text-green-400">Preview</label>
          <div className="flex-1 p-4 rounded-xl overflow-auto prose prose-invert prose-sm max-w-none"
               style={{ backgroundColor: 'rgba(15,15,26,0.6)', border: '1px solid var(--border)', minHeight: '400px' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        </div>
      </div>

      {/* Hint */}
      {isNew && (
        <div className="mt-4 p-3 rounded-xl text-xs flex items-start gap-2"
             style={{ backgroundColor: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)' }}>
          <span>💡</span>
          <span>Template đã được tự động điền. Thay thế các phần trong ngoặc (...) bằng thông tin thật của brand.</span>
        </div>
      )}
    </div>
  );
}
