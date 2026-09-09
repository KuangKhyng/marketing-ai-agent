import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useSearchParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import AuthGate from './components/AuthGate';
import Layout from './components/Layout';
import LoadingOverlay from './components/LoadingOverlay';
import SaveCampaign from './components/SaveCampaign';
import { campaignAPI } from './api/client';
const HistoryPage = lazy(() => import('./pages/HistoryPage'));
const LibraryPage = lazy(() => import('./pages/LibraryPage'));
const PlansPage = lazy(() => import('./pages/PlansPage'));
const InputPage = lazy(() => import('./pages/InputPage'));
const BriefReviewPage = lazy(() => import('./pages/BriefReviewPage'));
const StrategyReviewPage = lazy(() => import('./pages/StrategyReviewPage'));
const ContentReviewPage = lazy(() => import('./pages/ContentReviewPage'));
const FinalReviewPage = lazy(() => import('./pages/FinalReviewPage'));
const ExportPage = lazy(() => import('./pages/ExportPage'));
const BrandsPage = lazy(() => import('./pages/BrandsPage'));
const BrandDetailPage = lazy(() => import('./pages/BrandDetailPage'));
const DocumentEditorPage = lazy(() => import('./pages/DocumentEditorPage'));

const PHASES = ['input', 'brief_review', 'strategy_review', 'content_review', 'final_review', 'export'];

const PageWrapper = ({ children, phaseKey }) => (
  <motion.div
    key={phaseKey}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, scale: 0.98 }}
    transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
  >
    {children}
  </motion.div>
);

function CampaignFlow({ onReset }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const runParam = searchParams.get('run');

  const [phase, setPhase] = useState('input');
  const [campaignData, setCampaignData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [restoreError, setRestoreError] = useState(null);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  // Vào trang với ?run=<id> thì phải chờ dựng lại phiên trước khi vẽ bước nào
  const [restoring, setRestoring] = useState(Boolean(runParam));

  /* Mở lại link có ?run=<id>, hoặc F5 giữa luồng: đọc lại state từ server.
     Server giữ state 120 phút nên không có lý do gì để mất phiên chỉ vì reload. */
  useEffect(() => {
    if (!runParam || campaignData?.run_id === runParam) {
      setRestoring(false);
      return;
    }

    let cancelled = false;
    setRestoring(true);
    setRestoreError(null);
    (async () => {
      try {
        const { data } = await campaignAPI.get(runParam);
        if (cancelled) return;
        setCampaignData(data);
        setPhase(data.phase === 'completed' ? 'export' : data.phase);
      } catch (error) {
        if (!cancelled) setRestoreError(error.response?.status === 404
          ? 'Phiên làm việc đã hết hạn hoặc không tồn tại. Bạn có thể bắt đầu chiến dịch mới.'
          : 'Chưa kết nối được với máy chủ. Thử lại để tiếp tục chiến dịch đang làm.');
      } finally {
        if (!cancelled) setRestoring(false);
      }
    })();

    return () => { cancelled = true; };
  }, [runParam, restoreAttempt, campaignData?.run_id]);

  /* Giữ run_id trên URL để F5 hoặc gửi link cho người khác không mất phiên */
  useEffect(() => {
    const id = campaignData?.run_id;
    if (id && !searchParams.get('run')) {
      setSearchParams({ run: id }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignData?.run_id]);

  const handleReset = () => {
    setRestoreError(null);
    setPhase('input');
    setCampaignData(null);
    setSearchParams({}, { replace: true });
    if (onReset) onReset();
  };

  const pageProps = { campaignData, setCampaignData, setPhase, loading, setLoading };

  return (
    <Layout phase={phase} phases={PHASES} onReset={handleReset} showCampaignNav={true}>
      {!restoring && !restoreError && !loading && ['final_review', 'export'].includes(phase) && campaignData?.content?.pieces?.length > 0 && (
        <SaveCampaign key={campaignData.run_id} runId={campaignData.run_id} />
      )}
      {restoreError && (
        <section className="sheet p-7 space-y-4" role="alert">
          <h1 className="t-section">Chưa mở được chiến dịch</h1>
          <p className="text-ink-2">{restoreError}</p>
          <div className="flex flex-wrap gap-3">
            <button className="btn btn-primary" onClick={() => setRestoreAttempt(value => value + 1)}>Thử lại</button>
            <button className="btn btn-default" onClick={handleReset}>Tạo chiến dịch mới</button>
          </div>
          <p className="text-sm text-ink-2">Thử lại chỉ đọc phiên đã lưu, không gọi AI.</p>
        </section>
      )}
      {!restoring && !restoreError && <AnimatePresence mode="wait">
        {phase === 'input' && <PageWrapper phaseKey="input"><InputPage {...pageProps} /></PageWrapper>}
        {phase === 'brief_review' && <PageWrapper phaseKey="brief"><BriefReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'strategy_review' && <PageWrapper phaseKey="strategy"><StrategyReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'content_review' && <PageWrapper phaseKey="content"><ContentReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'final_review' && <PageWrapper phaseKey="final"><FinalReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'export' && <PageWrapper phaseKey="export"><ExportPage {...pageProps} /></PageWrapper>}
      </AnimatePresence>}

      <LoadingOverlay
        show={restoring}
        title="Đang mở lại phiên làm việc"
        description="Đọc lại chiến dịch đang dở từ server."
        hint="Chỉ mất một lát."
      />
    </Layout>
  );
}

export default function App() {
  return (
    <AuthGate>
      <BrowserRouter>
        <Suspense fallback={<p role="status" className="p-8">Đang tải màn hình…</p>}>
        <Routes>
          <Route path="/plans" element={<Layout showCampaignNav={false}><PlansPage /></Layout>} />
          <Route path="/plans/:planId" element={<Layout showCampaignNav={false}><PlansPage /></Layout>} />
          <Route path="/library" element={<Layout showCampaignNav={false}><LibraryPage /></Layout>} />
          <Route path="/library/:snapshotId" element={<Layout showCampaignNav={false}><LibraryPage /></Layout>} />
          <Route path="/" element={<CampaignFlow />} />
          <Route path="/history" element={<Layout showCampaignNav={false}><HistoryPage /></Layout>} />
          <Route path="/knowledge" element={
            <Layout showCampaignNav={false}>
              <BrandsPage />
            </Layout>
          } />
          <Route path="/knowledge/:brandId" element={
            <Layout showCampaignNav={false}>
              <BrandDetailPage />
            </Layout>
          } />
          <Route path="/knowledge/:brandId/edit/*" element={
            <Layout showCampaignNav={false}>
              <DocumentEditorPage />
            </Layout>
          } />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthGate>
  );
}
