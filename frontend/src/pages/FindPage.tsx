import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  MapPin,
  Sparkles,
  Home,
  ArrowUpDown,
  Info,
  ChevronLeft,
  SlidersHorizontal,
  Clock,
  Filter,
  Users,
  CheckCircle2,
  AlertCircle,
  Building,
  RotateCcw,
} from 'lucide-react';
import { HomeSearchForm } from '../components/RivoHome/HomeSearchForm';
import { ListingCard, SearchCriteriaContext } from '../components/RivoHome/ListingCard';
import { RivoGoogleMap, TravelModeKey } from '../components/RivoHome/RivoGoogleMap';
import {
  RecommendationRequest,
  RecommendationResult,
  WorkerOccupation,
} from '../types/api';
import {
  fetchOccupations,
  searchRecommendations,
} from '../services/api';

const LOADING_STAGES = [
  'Finding homes near your workplace...',
  'Checking affordability constraints...',
  'Calculating door-to-door commute options...',
  'Checking nearby schools, hospitals & essentials...',
  'Building your verified shortlist...',
];

export const FindPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [occupations, setOccupations] = useState<WorkerOccupation[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStageIdx, setLoadingStageIdx] = useState<number>(0);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [listings, setListings] = useState<RecommendationResult[]>([]);
  const [searchMetadata, setSearchMetadata] = useState<Record<string, unknown> | null>(null);
  const [selectedListing, setSelectedListing] = useState<RecommendationResult | null>(null);
  const [rejectedListings, setRejectedListings] = useState<RecommendationResult[]>([]);
  const [showRejected, setShowRejected] = useState<boolean>(false);
  const [hoveredListingId, setHoveredListingId] = useState<string | null>(null);

  // Active search criteria saved for user-relative comparison in cards
  const [activeCriteria, setActiveCriteria] = useState<SearchCriteriaContext | null>(null);

  // Travel mode selection (TRANSIT, TWO_WHEELER, DRIVE, WALK) — lives in results/map
  const [selectedTravelMode, setSelectedTravelMode] = useState<TravelModeKey>('TRANSIT');

  // Sorting and post-search filtering
  const [sortBy, setSortBy] = useState<'recommended' | 'rent_asc' | 'commute_asc' | 'travel_asc' | 'family'>('recommended');
  const [bhkFilter, setBhkFilter] = useState<number | 'all'>('all');

  // Active workplace starts EMPTY / NULL per user prompt
  const [currentWorkplace, setCurrentWorkplace] = useState<{
    lat: number;
    lon: number;
    label: string;
  } | null>(null);
  const [searchRadiusKm, setSearchRadiusKm] = useState<number>(18);

  useEffect(() => {
    fetchOccupations().then((occs) => setOccupations(occs));
  }, []);

  // Staged loading text animation
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (isLoading) {
      setLoadingStageIdx(0);
      let step = 0;
      timer = setInterval(() => {
        step = (step + 1) % LOADING_STAGES.length;
        setLoadingStageIdx(step);
      }, 500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isLoading]);

  const handleSearch = async (req: RecommendationRequest) => {
    setIsLoading(true);
    setHasSearched(true);

    const workplaceObj = {
      lat: req.workplace_lat,
      lon: req.workplace_lon,
      label: req.workplace_label || 'Workplace Destination',
    };
    setCurrentWorkplace(workplaceObj);
    setSearchRadiusKm(req.search_radius_km || 18);

    // Save criteria for user-relative property card comparisons
    setActiveCriteria({
      workplaceLabel: req.workplace_label,
      minRent: req.min_rent_monthly,
      maxRent: req.max_rent_monthly,
      bhk: req.bhk,
      maxCommuteMinutes: req.max_commute_minutes,
      selectedTravelMode: selectedTravelMode,
      householdIncome: req.worker?.household_income_monthly,
      schoolMaxMin: req.family?.school_max_minutes,
      hospitalMaxMin: req.family?.hospital_max_minutes,
      pharmacyMaxMin: req.family?.pharmacy_max_minutes,
    });

    try {
      const resp = await searchRecommendations(req);
      const rawResults = resp.results || [];
      const seenIds = new Set<string>();
      const results: RecommendationResult[] = [];
      for (const item of rawResults) {
        if (!seenIds.has(item.listing_id)) {
          seenIds.add(item.listing_id);
          results.push(item);
        }
      }
      setListings(results);
      setRejectedListings(resp.rejected_results || []);
      setSearchMetadata(resp.search_metadata || null);
      if (results.length > 0) {
        setSelectedListing(results[0]);
      } else {
        setSelectedListing(null);
      }
    } catch (err) {
      console.error('Search error', err);
      setListings([]);
      setRejectedListings([]);
      setSelectedListing(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter and sort listings with guaranteed uniqueness
  const filteredAndSortedListings = useMemo(() => {
    let result = [...listings];

    if (bhkFilter !== 'all') {
      result = result.filter((l) => l.bhk === bhkFilter);
    }

    // Hard Duplicate Guarantee: Never show duplicate properties
    const seen = new Set<string>();
    result = result.filter((l) => {
      if (seen.has(l.listing_id)) return false;
      seen.add(l.listing_id);
      return true;
    });

    if (sortBy === 'rent_asc') {
      result.sort((a, b) => (a.rent_monthly || 0) - (b.rent_monthly || 0));
    } else if (sortBy === 'commute_asc') {
      result.sort((a, b) => {
        const routeA = a.all_routes?.find((r) => r.mode === selectedTravelMode) || a.best_route;
        const routeB = b.all_routes?.find((r) => r.mode === selectedTravelMode) || b.best_route;
        const timeA = routeA?.duration_minutes ?? 999;
        const timeB = routeB?.duration_minutes ?? 999;
        return timeA - timeB;
      });
    } else if (sortBy === 'travel_asc') {
      result.sort((a, b) => {
        const costA = a.affordability?.monthly_transport_cost ?? 99999;
        const costB = b.affordability?.monthly_transport_cost ?? 99999;
        return costA - costB;
      });
    } else if (sortBy === 'family') {
      result.sort((a, b) => {
        const fitA = (a.school_access?.distance_m ?? 9999) + (a.hospital_access?.distance_m ?? 9999);
        const fitB = (b.school_access?.distance_m ?? 9999) + (b.hospital_access?.distance_m ?? 9999);
        return fitA - fitB;
      });
    }

    return result;
  }, [listings, sortBy, bhkFilter, selectedTravelMode]);

  const demoBanner = searchMetadata?.demo_banner ? String(searchMetadata.demo_banner) : null;
  const rentalSource = searchMetadata?.rental_source ? String(searchMetadata.rental_source) : 'Demo seed (CMRL-anchored)';

  return (
    <div className="space-y-8 animate-fadeIn max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 pb-16">
      {/* ============================================================ */}
      {/* STATE 1: SEARCH-FIRST INTERACTION (Shown BEFORE user search) */}
      {/* ============================================================ */}
      {!hasSearched ? (
        <div className="max-w-4xl mx-auto space-y-8 pt-4 sm:pt-8 animate-fadeIn">
          {/* Search Header */}
          <div className="text-center space-y-3">
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#F3F8FC] border border-[#BFDBFE] text-[#0878D1] text-xs font-bold tracking-wide">
              <Sparkles className="w-3.5 h-3.5 text-[#F5C542]" />
              <span>Door-to-Door Mobility &amp; Housing Discovery</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#06243A]">
              Find a home around your work and life.
            </h1>
            <p className="text-base text-[#607080] max-w-xl mx-auto leading-relaxed">
              Tell us where you work and what you need. RIVO will calculate homes around your commute, budget and daily essentials.
            </p>
          </div>

          {/* Professional Search Panel — Starts completely unselected */}
          <div className="bg-white rounded-3xl p-6 sm:p-10 border border-[#E2E8F0] shadow-xl relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#0878D1] via-[#13A8E8] to-[#F5C542]" />

            <HomeSearchForm
              occupations={occupations}
              onSearch={handleSearch}
              isLoading={isLoading}
              initialWorkplace={null}
            />
          </div>

          {/* Trust Line */}
          <div className="text-center text-xs text-[#607080]">
            RIVO compares rent, commute, transport cost and nearby essentials across Chennai.
          </div>

          {/* Helpful Pre-Search Guidance */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2 text-xs text-[#607080]">
            <div className="flex items-start space-x-3 p-4 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE]">
              <CheckCircle2 className="w-4 h-4 text-[#0878D1] shrink-0 mt-0.5" />
              <div>
                <b className="text-[#06243A] block mb-0.5">Real Destination Routing</b>
                MTC bus, CMRL metro, and walking transfers calculated door-to-door.
              </div>
            </div>
            <div className="flex items-start space-x-3 p-4 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE]">
              <CheckCircle2 className="w-4 h-4 text-[#0878D1] shrink-0 mt-0.5" />
              <div>
                <b className="text-[#06243A] block mb-0.5">Transparent Living Costs</b>
                Travel fares combined with rent against 40% income thresholds.
              </div>
            </div>
            <div className="flex items-start space-x-3 p-4 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE]">
              <CheckCircle2 className="w-4 h-4 text-[#0878D1] shrink-0 mt-0.5" />
              <div>
                <b className="text-[#06243A] block mb-0.5">Family Amenity Proximity</b>
                Verified distances to UDISE+ schools, hospitals, and pharmacies.
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ============================================================ */
        /* STATE 2: RECOMMENDATION RESULTS WORKSPACE (After search)     */
        /* ============================================================ */
        <div className="space-y-6 animate-fadeIn">
          {/* Active Search & Filter Header Banner */}
          <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold text-[#0878D1] uppercase tracking-wider bg-[#F3F8FC] px-2.5 py-0.5 rounded-full border border-[#BFDBFE]">
                  Active Search Scope
                </span>
                {activeCriteria?.minRent !== undefined && activeCriteria?.maxRent !== undefined && (
                  <span className="text-[10px] font-bold text-[#06243A] bg-slate-100 px-2 py-0.5 rounded-full">
                    ₹{(activeCriteria.minRent / 1000).toFixed(0)}k–₹{(activeCriteria.maxRent / 1000).toFixed(0)}k rent
                  </span>
                )}
                {activeCriteria?.bhk && (
                  <span className="text-[10px] font-bold text-[#06243A] bg-slate-100 px-2 py-0.5 rounded-full">
                    {activeCriteria.bhk} BHK
                  </span>
                )}
                {activeCriteria?.maxCommuteMinutes && (
                  <span className="text-[10px] font-bold text-[#06243A] bg-slate-100 px-2 py-0.5 rounded-full">
                    ≤{activeCriteria.maxCommuteMinutes} min commute
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-2 mt-1">
                <MapPin className="w-5 h-5 text-[#0878D1] shrink-0" />
                <span className="text-xl font-extrabold text-[#06243A]">
                  {currentWorkplace?.label || 'Workplace'}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setHasSearched(false);
                  setListings([]);
                  setSelectedListing(null);
                }}
                className="inline-flex items-center space-x-1.5 text-xs font-bold text-[#0878D1] hover:text-[#0764B0] px-4 py-2.5 rounded-xl border border-[#BFDBFE] bg-[#F3F8FC] hover:bg-[#EEF5FF] transition-colors cursor-pointer shadow-xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Change Search Criteria</span>
              </button>
            </div>
          </div>

          {/* Results Toolbar: Match Count + BHK Filters + Sort Dropdown */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-2 border-b border-[#E2E8F0]">
            <div>
              <div className="flex items-center space-x-2.5">
                <h2 className="text-xl font-extrabold text-[#06243A] tracking-tight">
                  Homes near {currentWorkplace?.label?.split('/')[0].trim()}
                </h2>
              </div>
              <p className="text-xs text-[#607080] mt-0.5">
                <b className="text-[#06243A]">{filteredAndSortedListings.length} homes</b> matching your income, commute limits, and family profile
              </p>
            </div>

            {/* Sort & BHK Controls */}
            <div className="flex flex-wrap items-center gap-2 self-stretch sm:self-auto">
              {/* BHK Filter Chips */}
              <div className="flex rounded-xl bg-[#F3F8FC] p-1 border border-[#E2E8F0] text-xs">
                {(['all', 1, 2, 3] as const).map((b) => (
                  <button
                    key={b}
                    onClick={() => setBhkFilter(b)}
                    className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                      bhkFilter === b
                        ? 'bg-[#0878D1] text-white shadow-xs'
                        : 'text-[#607080] hover:text-[#06243A]'
                    }`}
                  >
                    {b === 'all' ? 'All BHK' : `${b} BHK`}
                  </button>
                ))}
              </div>

              {/* Sort Dropdown */}
              <div className="flex items-center space-x-1.5 bg-white px-3 py-1.5 rounded-xl border border-[#E2E8F0] shadow-xs text-xs">
                <ArrowUpDown className="w-3.5 h-3.5 text-[#607080]" />
                <span className="text-[#607080]">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="bg-transparent font-bold text-[#06243A] outline-none cursor-pointer"
                >
                  <option value="recommended">Recommended Fit</option>
                  <option value="rent_asc">Rent: Low to High</option>
                  <option value="commute_asc">Shortest Commute</option>
                  <option value="travel_asc">Lowest Travel Cost</option>
                  <option value="family">Best Family Amenity Fit</option>
                </select>
              </div>
            </div>
          </div>

          {/* Truthful Sample Inventory Notification */}
          <div className="p-3 rounded-2xl bg-[#EEF5FF] border border-[#BFDBFE] flex items-center justify-between text-xs text-[#06243A] shadow-xs">
            <div className="flex items-center space-x-2.5">
              <Info className="w-4 h-4 shrink-0 text-[#0878D1]" />
              <span>
                <b>Sample Inventory Notice:</b> {demoBanner || '240 synthetic demonstration records across diverse Chennai localities. Not live market observations.'}
              </span>
            </div>
            <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded border border-[#BFDBFE] shrink-0 hidden sm:block text-[#0878D1]">
              {rentalSource}
            </span>
          </div>

          {/* Loading Experience with Staged Animation */}
          {isLoading ? (
            <div className="space-y-6 py-12">
              <div className="max-w-md mx-auto text-center space-y-4">
                <div className="w-12 h-12 rounded-full border-3 border-[#0878D1]/30 border-t-[#0878D1] animate-spin mx-auto" />
                <div className="space-y-1">
                  <h3 className="text-base font-extrabold text-[#06243A]">
                    {LOADING_STAGES[loadingStageIdx]}
                  </h3>
                  <p className="text-xs text-[#607080]">
                    Evaluating MTC fares, CMRL transit itineraries, and UDISE+ schools...
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 opacity-60 pointer-events-none">
                <div className="lg:col-span-5 space-y-4">
                  {[1, 2].map((n) => (
                    <div
                      key={n}
                      className="rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden animate-pulse"
                    >
                      <div className="h-48 bg-slate-200" />
                      <div className="p-5 space-y-3">
                        <div className="h-5 bg-slate-200 rounded-md w-1/3" />
                        <div className="h-4 bg-slate-200 rounded-md w-2/3" />
                        <div className="h-14 bg-slate-100 rounded-xl" />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="lg:col-span-7 h-[560px] rounded-2xl bg-slate-100 border border-[#E2E8F0] animate-pulse" />
              </div>
            </div>
          ) : filteredAndSortedListings.length > 0 && currentWorkplace ? (
            <>
              {/* Split View: ~45% Property Cards on Left, ~55% Sticky Google Map on Right */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left Column: Visual Property Cards */}
                <div className="lg:col-span-6 xl:col-span-5 space-y-6 max-h-[calc(100vh-140px)] overflow-y-auto pr-2">
                  {filteredAndSortedListings.map((item) => (
                    <ListingCard
                      key={item.listing_id}
                      listing={item}
                      isSelected={selectedListing?.listing_id === item.listing_id}
                      searchCriteria={{
                        ...activeCriteria,
                        selectedTravelMode,
                      }}
                      onSelect={(it) => setSelectedListing(it)}
                      onHover={(id) => setHoveredListingId(id)}
                      onViewRouteModal={(it) => {
                        navigate(`/property/${it.listing_id}`, {
                          state: { listing: it, searchCriteria: activeCriteria },
                        });
                      }}
                    />
                  ))}
                </div>

                {/* Right Column: Sticky Dominant Google Map with Travel Mode Toolbar */}
                <div className="lg:col-span-6 xl:col-span-7 lg:sticky lg:top-24 h-[560px] lg:h-[calc(100vh-140px)] rounded-2xl overflow-hidden border border-[#E2E8F0] shadow-md">
                  <RivoGoogleMap
                    workplace={currentWorkplace}
                    searchRadiusKm={searchRadiusKm}
                    listings={filteredAndSortedListings}
                    selectedListingId={selectedListing?.listing_id || null}
                    hoveredListingId={hoveredListingId}
                    selectedTravelMode={selectedTravelMode}
                    onSelectTravelMode={(mode) => setSelectedTravelMode(mode)}
                    onSelectListing={(it) => setSelectedListing(it)}
                  />
                </div>
              </div>

              {/* Properties Evaluated But Outside Criteria ("Why Not?" Decision Engine) */}
              {rejectedListings.length > 0 && (
                <div className="mt-8 pt-6 border-t border-[#E2E8F0] space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-bold text-[#06243A] flex items-center space-x-2">
                        <span>Properties Evaluated But Outside Criteria</span>
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-[#607080] text-xs font-semibold">
                          {rejectedListings.length} evaluated
                        </span>
                      </h4>
                      <p className="text-xs text-[#607080] mt-0.5">
                        RIVO tests actual routes and budgets for candidate homes. These homes were rejected because they violated your hard constraints.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowRejected(!showRejected)}
                      className="px-3 py-1.5 rounded-lg border border-[#CBD5E1] bg-white hover:bg-slate-50 text-xs font-bold text-[#0878D1] transition-colors cursor-pointer"
                    >
                      {showRejected ? 'Hide Evaluated Homes' : `View Evaluated Homes (${rejectedListings.length})`}
                    </button>
                  </div>

                  {showRejected && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
                      {rejectedListings.slice(0, 9).map((rej) => {
                        const rejRoute = rej.all_routes?.find((r) => r.mode === selectedTravelMode) || rej.best_route;
                        const rejCommute = rejRoute?.duration_minutes ?? rejRoute?.duration_min;
                        return (
                          <div
                            key={rej.listing_id}
                            className="p-4 rounded-xl border border-rose-200 bg-rose-50/30 space-y-2 text-xs text-[#06243A]"
                          >
                            <div className="flex items-baseline justify-between">
                              <span className="font-extrabold text-sm text-[#06243A]">
                                ₹{(rej.rent_monthly || 0).toLocaleString()} <span className="text-[11px] font-normal text-[#607080]">/mo</span>
                              </span>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-rose-700 bg-rose-100 px-2 py-0.5 rounded">
                                Rejected
                              </span>
                            </div>
                            <div className="text-[#607080] font-medium text-xs">
                              {rej.bhk || 2} BHK · {rej.area_sqft || 800} sq ft · <span className="capitalize">{rej.locality || 'Chennai'}</span>
                            </div>
                            <div className="space-y-1 pt-1.5 border-t border-rose-200/60">
                              <div className="text-[10px] font-bold uppercase text-[#607080]">Why Not Recommended?</div>
                              {rej.rejection_reasons?.map((rr, idx) => (
                                <div key={idx} className="flex items-start space-x-1.5 text-rose-800 font-semibold leading-tight">
                                  <span className="text-rose-600 font-bold shrink-0">✕</span>
                                  <span>{rr}</span>
                                </div>
                              ))}
                              {rejCommute && (
                                <div className="flex items-start space-x-1.5 text-[#06243A] leading-tight">
                                  <span className="text-emerald-600 font-bold shrink-0">ℹ</span>
                                  <span>Actual commute: {rejCommute} min ({rejRoute?.distance_km?.toFixed(1) || '—'} km)</span>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            /* Empty State */
            <div className="text-center py-16 px-6 bg-white rounded-2xl border border-[#E2E8F0] shadow-xs space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-[#EEF5FF] border border-[#BFDBFE] flex items-center justify-center text-[#0878D1] mx-auto">
                <Home className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-[#06243A]">
                No homes match all your current requirements
              </h3>
              <p className="text-xs text-[#607080] max-w-md mx-auto leading-relaxed">
                Try expanding your maximum commute time, increasing your rent budget ceiling, or relaxing the bedroom configuration.
              </p>
              <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setBhkFilter('all');
                    if (currentWorkplace) {
                      handleSearch({
                        min_rent_monthly: undefined,
                        max_rent_monthly: 35000,
                        workplace_lat: currentWorkplace.lat,
                        workplace_lon: currentWorkplace.lon,
                        workplace_label: currentWorkplace.label,
                        max_commute_minutes: 75,
                        preferred_modes: ['TRANSIT', 'TWO_WHEELER', 'DRIVE', 'WALK'],
                        search_radius_km: 25.0,
                        page: 1,
                        page_size: 25,
                      });
                    }
                  }}
                  className="px-5 py-2.5 rounded-xl bg-[#0878D1] hover:bg-[#0764B0] text-white text-xs font-bold transition-colors cursor-pointer shadow-xs"
                >
                  Expand Search Radius &amp; Budget
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setHasSearched(false);
                    setListings([]);
                    setSelectedListing(null);
                  }}
                  className="px-5 py-2.5 rounded-xl bg-[#F3F8FC] hover:bg-[#EEF5FF] text-[#0878D1] border border-[#BFDBFE] text-xs font-bold transition-colors cursor-pointer shadow-xs"
                >
                  Change Search Workplace
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
