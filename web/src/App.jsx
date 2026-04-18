import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Layout from './components/Layout';
import InputPage from './pages/InputPage';
import BriefReviewPage from './pages/BriefReviewPage';
import StrategyReviewPage from './pages/StrategyReviewPage';
import ContentReviewPage from './pages/ContentReviewPage';
import FinalReviewPage from './pages/FinalReviewPage';
import ExportPage from './pages/ExportPage';

const PHASES = ['input', 'brief_review', 'strategy_review', 'content_review', 'final_review', 'export'];

const PageWrapper = ({ children, key }) => (
  <motion.div
    key={key}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, scale: 0.98 }}
    transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
  >
    {children}
  </motion.div>
);

export default function App() {
  const [phase, setPhase] = useState('input');
  const [campaignData, setCampaignData] = useState(null);
  const [loading, setLoading] = useState(false);

  const pageProps = { campaignData, setCampaignData, setPhase, loading, setLoading };

  return (
    <Layout phase={phase} phases={PHASES} onReset={() => { setPhase('input'); setCampaignData(null); }}>
      <AnimatePresence mode="wait">
        {phase === 'input' && <PageWrapper key="input"><InputPage {...pageProps} /></PageWrapper>}
        {phase === 'brief_review' && <PageWrapper key="brief"><BriefReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'strategy_review' && <PageWrapper key="strategy"><StrategyReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'content_review' && <PageWrapper key="content"><ContentReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'final_review' && <PageWrapper key="final"><FinalReviewPage {...pageProps} /></PageWrapper>}
        {phase === 'export' && <PageWrapper key="export"><ExportPage {...pageProps} /></PageWrapper>}
      </AnimatePresence>
    </Layout>
  );
}
