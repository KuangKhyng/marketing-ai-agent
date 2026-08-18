import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useSearchParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import AuthGate from './components/AuthGate';
import Layout from './components/Layout';
import LoadingOverlay from './components/LoadingOverlay';
import { campaignAPI } from './api/client';
import InputPage from './pages/InputPage';
import BriefReviewPage from './pages/BriefReviewPage';
import StrategyReviewPage from './pages/StrategyReviewPage';
import ContentReviewPage from './pages/ContentReviewPage';
import FinalReviewPage from './pages/FinalReviewPage';
import ExportPage from './pages/ExportPage';
import BrandsPage from './pages/BrandsPage';
import BrandDetailPage from './pages/BrandDetailPage';
import DocumentEditorPage from './pages/DocumentEditorPage';

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
  // Vào trang với ?run=<id> thì phải chờ dựng lại phiên trước khi vẽ bước nào
  const [restoring, setRestoring] = useState(Boolean(runParam));

  /* Mở lại link có ?run=<id>, hoặc F5 giữa luồng: đọc lại state từ server.
     Server giữ state 120 phút nên không có lý do gì để mất phiên chỉ vì reload. */
  useEffect(() => {
    if (!runParam || campaignData) {
      setRestoring(false);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const { data } = await campaignAPI.get(runParam);
        if (cancelled) return;
        setCampaignData(data);
        setPhase(data.phase === 'completed' ? 'export' : data.phase);
      } catch {
        // Phiên hết hạn hoặc không tồn tại — bỏ param, bắt đầu lại từ đầu
        if (!cancelled) setSearchParams({}, { replace: true });
      } finally {
        if (!cancelled) setRestoring(false);
      }
    })();

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runParam]);

  /* Giữ run_id trên URL để F5 hoặc gửi link cho người khác không mất phiên */
  useEffect(() => {
    const id = campaignData?.run_id;
    if (id && searchParams.get('run') !== id) {
      setSearchParams({ run: id }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignData?.run_id]);

  const handleReset = () => {
    setPhase('input');
    setCampaignData(null);
    setSearchParams({}, { replace: true });
    if (onReset) onReset();
  };

  const pageProps = { campaignData, setCampaignData, setPhase, loading, setLoading };

  return (
    <Layout phase={phase} phases={PHASES} onReset={handleReset} showCampaignNav={true}>
      <AnimatePresence mode="wait">
        {phase === 'input' && <PageWrapper phaseKey="input"><InputPage {...pageProps} /></PageWrapper>}
        {phase === 'brief_review' && <PageWrapper phaseKey="brief"><BriefReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'strategy_review' && <PageWrapper phaseKey="strategy"><StrategyReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'content_review' && <PageWrapper phaseKey="content"><ContentReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'final_review' && <PageWrapper phaseKey="final"><FinalReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'export' && <PageWrapper phaseKey="export"><ExportPage {...pageProps} /></PageWrapper>}
      </AnimatePresence>

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
        <Routes>
          <Route path="/" element={<CampaignFlow />} />
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
      </BrowserRouter>
    </AuthGate>
  );
}
