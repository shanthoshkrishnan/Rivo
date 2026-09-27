import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { HomePage } from './pages/HomePage';
import { FindPage } from './pages/FindPage';
import { PropertyDetailPage } from './pages/PropertyDetailPage';
import { CityPage } from './pages/CityPage';
import { DataSourcesPage } from './pages/DataSourcesPage';

// Scroll to top helper on route change
const ScrollToTop: React.FC = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <div className="min-h-screen bg-[#FFFFFF] text-[#0B1F33] flex flex-col font-sans selection:bg-[#0878D1]/20 selection:text-[#06243A]">
        {/* Sticky Translucent Header with Official RivoLogo & Honest Status Popover */}
        <Header />

        {/* Multi-Page Route Content Canvas */}
        <main className="flex-1 w-full pt-6">
          <Routes>
            {/* Route 1: Real-Estate Product Landing Page */}
            <Route path="/" element={<HomePage />} />

            {/* Route 2: Rental Finder (Progressive Search-First Workflow) */}
            <Route path="/find" element={<FindPage />} />

            {/* Route 3: Dedicated Real-Estate Property Detail Page */}
            <Route path="/property/:id" element={<PropertyDetailPage />} />

            {/* Route 4: RIVO City Planner Scenario Engine */}
            <Route path="/city" element={<CityPage />} />

            {/* Route 5: Authoritative Data Sources Trust Center */}
            <Route path="/data-sources" element={<DataSourcesPage />} />

            {/* Fallback to Home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* Premium Deep Navy Footer */}
        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
