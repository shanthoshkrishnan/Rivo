import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { HomeSearchForm } from './components/RivoHome/HomeSearchForm';
import { ListingCard } from './components/RivoHome/ListingCard';
import { ListingDetailModal } from './components/RivoHome/ListingDetailModal';
import { RivoMap } from './components/RivoHome/RivoMap';
import { CityPlanner } from './components/RivoCity/CityPlanner';
import { DataSourcesView } from './components/DataSources/DataSourcesView';
import {
  RecommendationRequest,
  RecommendationResult,
  WorkerOccupation,
} from './types/api';
import {
  checkBackendHealth,
  fetchOccupations,
  searchRecommendations,
} from './services/api';
import { Search, MapPin, Sparkles, Filter, AlertCircle, Home } from 'lucide-react';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'home' | 'city' | 'sources'>('home');
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [occupations, setOccupations] = useState<WorkerOccupation[]>([]);

  // Search & Listings State
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [listings, setListings] = useState<RecommendationResult[]>([]);
  const [selectedListing, setSelectedListing] = useState<RecommendationResult | null>(null);
  const [detailModalListing, setDetailModalListing] = useState<RecommendationResult | null>(null);

  const [currentWorkplace, setCurrentWorkplace] = useState({
    lat: 13.0827,
    lon: 80.2707,
    label: 'Chennai Central',
  });
  const [searchRadiusKm, setSearchRadiusKm] = useState<number>(18);

  // Check health and load occupations on mount
  useEffect(() => {
    checkBackendHealth().then((h) => setBackendOnline(h != null && h.status === 'ok'));
    fetchOccupations().then((occs) => {
      setOccupations(occs);
    });

    // Auto-run an initial search for Nurse at Chennai Central so the page is populated
    handleSearch({
      max_rent_monthly: 15000,
      bhk: 2,
      workplace_lat: 13.0827,
      workplace_lon: 80.2707,
      workplace_label: 'Chennai Central',
      max_commute_minutes: 60,
      preferred_modes: ['TRANSIT', 'TWO_WHEELER', 'WALK'],
      worker: {
        occupation_key: 'nurse',
        household_income_monthly: 24000,
      },
      family: {
        adults: 2,
        children: 1,
        child_age_bands: ['6-12'],
        school_max_minutes: 20,
        hospital_max_minutes: 25,
        pharmacy_max_minutes: 10,
      },
      search_radius_km: 18.0,
      work_days_per_month: 22,
      page: 1,
      page_size: 20,
    });
  }, []);

  const handleSearch = async (req: RecommendationRequest) => {
    setIsLoading(true);
    setHasSearched(true);
    setCurrentWorkplace({
      lat: req.workplace_lat,
      lon: req.workplace_lon,
      label: req.workplace_label || 'Workplace',
    });
    setSearchRadiusKm(req.search_radius_km || 18);

    try {
      const resp = await searchRecommendations(req);
      setListings(resp.results || []);
      if (resp.results && resp.results.length > 0) {
        setSelectedListing(resp.results[0]);
      } else {
        setSelectedListing(null);
      }
    } catch (err) {
      console.error('Search error', err);
      setListings([]);
      setSelectedListing(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-[#2C2523] flex flex-col font-sans">
      <Header
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        backendOnline={backendOnline}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* RIVO HOME WORKFLOW */}
        {currentTab === 'home' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Minimalist Hero */}
            <div className="text-center sm:text-left max-w-2xl">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#2C2523]">
                Find a home that fits your life — not just your budget.
              </h1>
              <p className="text-xs sm:text-sm text-[#6B615B] mt-1.5 leading-relaxed">
                Chennai-first housing + door-to-door mobility intelligence. Connect your workplace, family needs, and income to real rental options.
              </p>
            </div>

            {/* Stepped Form Card */}
            <HomeSearchForm
              occupations={occupations}
              onSearch={handleSearch}
              isLoading={isLoading}
            />

            {/* Results Section */}
            <div className="pt-2">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-[#2C2523]">
                    Recommended Homes for Your Commute
                  </h2>
                  <p className="text-xs text-[#8C7E75]">
                    {listings.length} homes within budget &amp; commute constraints around {currentWorkplace.label}
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-xs font-medium text-[#7A6F68] bg-[#F3ECE4] px-2.5 py-1 rounded-full border border-[#E5DDD2]">
                    Sorted by: Total Affordability + Travel Fit
                  </span>
                </div>
              </div>

              {/* Loading Skeleton */}
              {isLoading ? (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  <div className="lg:col-span-5 space-y-4">
                    {[1, 2, 3].map((n) => (
                      <div
                        key={n}
                        className="rounded-2xl p-5 border border-[#EBE4DC] bg-white space-y-3 animate-pulse"
                      >
                        <div className="h-5 bg-[#F5EFEB] rounded-md w-1/3" />
                        <div className="h-4 bg-[#F5EFEB] rounded-md w-2/3" />
                        <div className="h-10 bg-[#FAF8F5] rounded-xl w-full" />
                      </div>
                    ))}
                  </div>
                  <div className="lg:col-span-7 h-[420px] rounded-2xl bg-[#F5EFEB] border border-[#EBE4DC] animate-pulse" />
                </div>
              ) : listings.length > 0 ? (
                /* Uncongested Split View: Listings on Left, Interactive Map on Right */
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Left Column: Spacious Property Cards */}
                  <div className="lg:col-span-5 space-y-4 max-h-[720px] overflow-y-auto pr-1">
                    {listings.map((item) => (
                      <ListingCard
                        key={item.listing_id}
                        listing={item}
                        isSelected={selectedListing?.listing_id === item.listing_id}
                        onSelect={(it) => setSelectedListing(it)}
                        onViewRouteModal={(it) => setDetailModalListing(it)}
                      />
                    ))}
                  </div>

                  {/* Right Column: Sticky Interactive Chennai Map */}
                  <div className="lg:col-span-7 lg:sticky lg:top-24 h-[420px] lg:h-[680px]">
                    <RivoMap
                      workplace={currentWorkplace}
                      searchRadiusKm={searchRadiusKm}
                      listings={listings}
                      selectedListingId={selectedListing?.listing_id || null}
                      onSelectListing={(it) => setSelectedListing(it)}
                    />
                  </div>
                </div>
              ) : hasSearched ? (
                /* Empty State */
                <div className="text-center py-16 px-4 bg-white rounded-3xl border border-[#EBE4DC]">
                  <Home className="w-10 h-10 text-[#C25E38] mx-auto mb-3 opacity-50" />
                  <h3 className="text-base font-bold text-[#2C2523]">No listings match these strict constraints</h3>
                  <p className="text-xs text-[#8C7E75] max-w-sm mx-auto mt-1">
                    Try expanding your maximum commute time or increasing the rent budget ceiling by ₹1,000–₹2,000.
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        )}

        {/* RIVO CITY WORKFLOW */}
        {currentTab === 'city' && (
          <CityPlanner occupations={occupations} />
        )}

        {/* DATA SOURCES REGISTRY */}
        {currentTab === 'sources' && (
          <DataSourcesView />
        )}
      </main>

      {/* Route & Detail Modal */}
      <ListingDetailModal
        listing={detailModalListing}
        onClose={() => setDetailModalListing(null)}
      />

      {/* Footer */}
      <footer className="mt-auto border-t border-[#EBE4DC] bg-[#FAF8F5] py-6 text-xs text-[#8C7E75]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            <b>RIVO</b> • Team CLAIRES (ST1010) • PS-11-S3 Worker Housing &amp; Mobility Intelligence
          </div>
          <div className="flex items-center space-x-4 text-[11px]">
            <span>Chennai Pilot</span>
            <span>•</span>
            <span>CUMTA GTFS</span>
            <span>•</span>
            <span>PLFS 2025</span>
            <span>•</span>
            <span>UDISE+</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
