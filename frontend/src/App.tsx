import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { ModelsPage, ModelDetailPage } from './pages/ModelsPage';
import { ModelFamilyPage } from './pages/ModelFamilyPage';
import { CSVAnalysisPage } from './pages/CSVAnalysisPage';
import { SingleTransactionPage } from './pages/SingleTransactionPage';
import { AboutPage } from './pages/AboutPage';
import { PrivacyPolicyPage } from './pages/PrivacyPolicyPage';
import { TermsPage } from './pages/TermsPage';
import { SignInPage } from './pages/SignInPage';
import { SignUpPage } from './pages/SignUpPage';
import { UserDashboardPage } from './pages/UserDashboardPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import './index.css';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
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

            {/* 5. Authentication (Separate Sign-In and Sign-Up) */}
            <Route path="signin" element={<SignInPage />} />
            <Route path="signup" element={<SignUpPage />} />
            <Route path="login" element={<Navigate to="/signin" replace />} />
            <Route path="register" element={<Navigate to="/signup" replace />} />

            {/* 6. User Dashboard (Protected) */}
            <Route
              path="dashboard"
              element={
                <ProtectedRoute>
                  <UserDashboardPage />
                </ProtectedRoute>
              }
            />

            {/* 7. Admin Console (Admin Only) */}
            <Route
              path="admin"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminDashboardPage />
                </ProtectedRoute>
              }
            />

            {/* 8. About / Project Information */}
            <Route path="about" element={<AboutPage />} />

            {/* 9. Privacy Policy */}
            <Route path="privacy" element={<PrivacyPolicyPage />} />

            {/* 10. Terms and Conditions */}
            <Route path="terms" element={<TermsPage />} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
