import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { ModelsPage, ModelDetailPage } from './pages/ModelsPage';
import { ModelFamilyPage } from './pages/ModelFamilyPage';
import { CSVAnalysisPage } from './pages/CSVAnalysisPage';
import { SingleTransactionPage } from './pages/SingleTransactionPage';
import { AboutPage } from './pages/AboutPage';
import { PrivacyPolicyPage } from './pages/PrivacyPolicyPage';
import { TermsPage } from './pages/TermsPage';
import './index.css';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* 1. Home */}
          <Route index element={<HomePage />} />

          {/* 2. Models & Model Families */}
          <Route path="models" element={<ModelsPage />} />
          <Route path="models/xgboost" element={<ModelFamilyPage />} />
          <Route path="models/mlp" element={<ModelFamilyPage />} />
          <Route path="models/autoencoder" element={<ModelFamilyPage />} />
          <Route path="models/family/:familyId" element={<ModelFamilyPage />} />
          <Route path="models/:modelId" element={<ModelDetailPage />} />

          {/* 3. CSV Analysis */}
          <Route path="csv" element={<CSVAnalysisPage />} />

          {/* 4. Individual Transaction */}
          <Route path="transaction" element={<SingleTransactionPage />} />
          <Route path="predict" element={<Navigate to="/transaction" replace />} />

          {/* 5. About / Project Information */}
          <Route path="about" element={<AboutPage />} />

          {/* 6. Privacy Policy */}
          <Route path="privacy" element={<PrivacyPolicyPage />} />

          {/* 7. Terms and Conditions */}
          <Route path="terms" element={<TermsPage />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
