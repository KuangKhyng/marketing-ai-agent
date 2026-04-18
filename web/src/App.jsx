import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Layout from './components/Layout';
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
  const [phase, setPhase] = useState('input');
  const [campaignData, setCampaignData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleReset = () => {
    setPhase('input');
    setCampaignData(null);
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
    </Layout>
  );
}

export default function App() {
  return (
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
  );
}
