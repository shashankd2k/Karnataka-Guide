import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from './components/layout/Shell';
import { HomePage } from './pages/HomePage';
import { GuidePage } from './pages/GuidePage';
import { ExplorePage } from './pages/ExplorePage';
import { DestinationDetailPage } from './pages/DestinationDetailPage';
import { MapPage } from './pages/MapPage';
import { AboutPage } from './pages/AboutPage';

// Admin Components & Pages
import { ProtectedRoute } from './components/admin/ProtectedRoute';
import { AdminShell } from './components/admin/AdminShell';
import { AdminLoginPage } from './pages/admin/AdminLoginPage';
import { AdminDashboardOverviewPage } from './pages/admin/AdminDashboardOverviewPage';
import { AdminDocumentsPage } from './pages/admin/AdminDocumentsPage';
import { AdminKnowledgePage } from './pages/admin/AdminKnowledgePage';
import { AdminGenerationDetailPage } from './pages/admin/AdminGenerationDetailPage';
import { AdminRetrievalTestPage } from './pages/admin/AdminRetrievalTestPage';
import { AdminTranslationsPage } from './pages/admin/AdminTranslationsPage';
import { AdminSystemPage } from './pages/admin/AdminSystemPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Tourist Portal Routes */}
          <Route path="/" element={<Shell />}>
            <Route index element={<HomePage />} />
            <Route path="guide" element={<GuidePage />} />
            <Route path="explore" element={<ExplorePage />} />
            <Route path="explore/:slug" element={<DestinationDetailPage />} />
            <Route path="map" element={<MapPage />} />
            <Route path="about" element={<AboutPage />} />
          </Route>

          {/* Admin Unauthenticated Login */}
          <Route path="/admin/login" element={<AdminLoginPage />} />

          {/* Admin Protected Console */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<AdminDashboardOverviewPage />} />
            <Route path="documents" element={<AdminDocumentsPage />} />
            <Route path="knowledge" element={<AdminKnowledgePage />} />
            <Route path="knowledge/:id" element={<AdminGenerationDetailPage />} />
            <Route path="retrieval-test" element={<AdminRetrievalTestPage />} />
            <Route path="translations" element={<AdminTranslationsPage />} />
            <Route path="system" element={<AdminSystemPage />} />
          </Route>

          {/* Wildcard Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
