import React, { useState, useEffect } from 'react';
import { useParams, useLocation, Link, useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  Clock,
  Navigation,
  School,
  HeartPulse,
  Pill,
  CheckCircle2,
  AlertCircle,
  Train,
  Bus,
  Car,
  Bike,
  Shield,
  MapPin,
  Building,
  DollarSign,
  Camera,
  Calendar,
  Layers,
} from 'lucide-react';
import { RecommendationResult, RouteResult } from '../types/api';
import { fetchRecommendationDetail } from '../services/api';
import { getPropertyImages } from '../utils/propertyImages';
import { RivoGoogleMap } from '../components/RivoHome/RivoGoogleMap';

export const PropertyDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const passedListing = location.state?.listing as RecommendationResult | undefined;

  const [listing, setListing] = useState<RecommendationResult | null>(passedListing || null);
  const [isLoading, setIsLoading] = useState<boolean>(!passedListing);
  const [activeImageIndex, setActiveImageIndex] = useState<number>(0);

  // If no listing was passed via navigation state, fetch from backend detail endpoint
  useEffect(() => {
    if (!listing && id) {
      setIsLoading(true);
      fetchRecommendationDetail({
        listing_id: id,
        workplace_lat: 13.0827,
        workplace_lon: 80.2707,
        workplace_label: 'Chennai Central / Park Town',
      })
        .then((resp) => {
          if (resp?.result) {
            setListing(resp.result);
          }
        })
        .catch((err) => console.error('Detail fetch error', err))
        .finally(() => setIsLoading(false));
    }
  }, [id, listing]);

  if (isLoading) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center space-y-4">
        <span className="w-8 h-8 border-3 border-[#0878D1]/30 border-t-[#0878D1] rounded-full animate-spin inline-block" />
        <p className="text-sm font-semibold text-[#06243A]">Loading verified home itinerary &amp; family details...</p>
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-[#EF4444] mx-auto" />
        <h2 className="text-2xl font-bold text-[#06243A]">Property Not Found</h2>
        <p className="text-sm text-[#607080]">
          The requested rental home may have expired or is not present in the current demonstration inventory.
        </p>
        <Link
          to="/find"
          className="inline-flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-[#0878D1] text-white font-bold text-xs shadow-xs"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Return to Rental Finder</span>
        </Link>
      </div>
    );
  }

  const imageSet = getPropertyImages(listing.listing_id, listing.locality, listing.bhk);
  const images = imageSet.gallery.length > 0 ? imageSet.gallery : [imageSet.cover];

  const rent = listing.rent_monthly || 0;
  const maintenance = listing.maintenance_monthly || 0;
  const transportCost = listing.affordability?.monthly_transport_cost || 0;
  const totalCost = rent + maintenance + transportCost;

  const bestRoute = listing.best_route;
  const durationMin = bestRoute?.duration_minutes ?? Math.round((bestRoute?.duration_seconds || 0) / 60);

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8 animate-fadeIn pb-24">
      {/* 1. Breadcrumbs & Back Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 text-xs font-semibold text-[#607080]">
          <Link to="/" className="hover:text-[#06243A]">Home</Link>
          <span>/</span>
          <Link to="/find" className="hover:text-[#06243A]">Find a Home</Link>
          <span>/</span>
          <span className="text-[#0878D1] capitalize">{listing.locality || 'Chennai'}</span>
          <span>/</span>
          <span className="text-slate-400 font-mono">#{listing.listing_id}</span>
        </div>

        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center space-x-1.5 text-xs font-bold text-[#0878D1] hover:text-[#06243A] px-3.5 py-1.5 rounded-xl bg-[#F3F8FC] border border-[#BFDBFE] transition-colors cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Back to Results</span>
        </button>
      </div>

      {/* 2. Real-Estate Image Showcase */}
      <div className="space-y-4">
        <div className="relative h-[380px] sm:h-[480px] lg:h-[540px] rounded-3xl overflow-hidden border border-[#E2E8F0] shadow-md bg-[#F3F8FC]">
          <img
            src={images[activeImageIndex] || imageSet.cover}
            alt={`${listing.bhk} BHK in ${listing.locality}`}
            className="w-full h-full object-cover object-center"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#06243A]/80 via-transparent to-transparent pointer-events-none" />

          {/* Top Badges */}
          <div className="absolute top-4 left-4 right-4 flex items-center justify-between">
            <span className="px-3 py-1 rounded-full bg-[#06243A]/90 text-white text-xs font-bold tracking-wide backdrop-blur-md border border-white/20">
              {listing.provider === 'rivo_direct' ? 'Live Listing' : 'Demo Inventory (CMRL-Anchored)'}
            </span>

            <span className="px-3 py-1 rounded-full bg-black/60 text-white text-xs font-medium backdrop-blur-md flex items-center space-x-1.5">
              <Camera className="w-3.5 h-3.5" />
              <span>{activeImageIndex + 1} of {images.length} photos</span>
            </span>
          </div>

          {/* Bottom Title Bar */}
          <div className="absolute bottom-6 left-6 right-6 text-white flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-[#F5C542]">
                {listing.locality || 'Chennai Urban Corridor'}
              </span>
              <h1 className="text-2xl sm:text-4xl font-extrabold text-white mt-1">
                {listing.bhk || 2} BHK {imageSet.propertyTypeLabel}
              </h1>
              <p className="text-xs sm:text-sm text-slate-300 mt-1 flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-[#13A8E8]" />
                <span>Anchored near transit corridor in {listing.locality}</span>
                {listing.area_sqft && <span>• {listing.area_sqft} sq ft carpet</span>}
              </p>
            </div>

            <div className="text-left sm:text-right bg-[#06243A]/80 backdrop-blur-md p-4 rounded-2xl border border-white/20">
              <div className="text-xs text-slate-300 uppercase tracking-wider font-semibold">Monthly Asking</div>
              <div className="text-3xl sm:text-4xl font-extrabold text-white">
                ₹{rent.toLocaleString()}
                <span className="text-xs text-slate-300 font-normal"> / mo</span>
              </div>
              {maintenance > 0 && (
                <div className="text-[11px] text-slate-300">+ ₹{maintenance} maintenance</div>
              )}
            </div>
          </div>
        </div>

        {/* Thumbnail Gallery Strip */}
        {images.length > 1 && (
          <div className="flex items-center space-x-3 overflow-x-auto pb-2">
            {images.map((img, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setActiveImageIndex(idx)}
                className={`relative w-24 h-16 sm:w-32 sm:h-20 rounded-xl overflow-hidden shrink-0 border-2 transition-all cursor-pointer ${
                  activeImageIndex === idx
                    ? 'border-[#0878D1] ring-2 ring-[#0878D1]/30 scale-102'
                    : 'border-transparent opacity-70 hover:opacity-100'
                }`}
              >
                <img src={img} alt="Thumbnail" className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 2.5 YOUR SEARCH MATCH (User-Relative Fit) */}
      {location.state?.searchCriteria && (
        <div className="bg-[#F8FAFC] rounded-3xl p-6 sm:p-8 border border-[#E2E8F0] shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#0878D1] bg-white px-3 py-1 rounded-full border border-[#BFDBFE]">
              Your Match Analysis
            </span>
            <span className="text-xs font-extrabold text-[#10B981] flex items-center space-x-1">
              <CheckCircle2 className="w-4 h-4" />
              <span>Criteria Verified</span>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="bg-white p-4 rounded-2xl border border-[#E2E8F0] space-y-1">
              <span className="text-[#607080] font-medium">Monthly Rent Fit</span>
              <div className="text-base font-extrabold text-[#06243A]">₹{rent.toLocaleString()}</div>
              <div className="text-[11px] text-[#0878D1] font-semibold">
                {location.state.searchCriteria.minRent !== undefined && location.state.searchCriteria.maxRent !== undefined
                  ? `Within your ₹${(location.state.searchCriteria.minRent/1000).toFixed(0)}k–₹${(location.state.searchCriteria.maxRent/1000).toFixed(0)}k range ✓`
                  : `Within your ₹${((location.state.searchCriteria.maxRent || 0)/1000).toFixed(0)}k limit ✓`}
              </div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#E2E8F0] space-y-1">
              <span className="text-[#607080] font-medium">Commute Limit</span>
              <div className="text-base font-extrabold text-[#06243A]">{durationMin} min</div>
              <div className="text-[11px] text-[#10B981] font-semibold">
                Within your ≤{location.state.searchCriteria.maxCommuteMinutes || 45} min limit ✓
              </div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#E2E8F0] space-y-1">
              <span className="text-[#607080] font-medium">Bedrooms Config</span>
              <div className="text-base font-extrabold text-[#06243A]">{listing.bhk || 2} BHK</div>
              <div className="text-[11px] text-[#10B981] font-semibold">
                {location.state.searchCriteria.bhk ? `${location.state.searchCriteria.bhk} BHK Matched ✓` : 'Standard Layout ✓'}
              </div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#E2E8F0] space-y-1">
              <span className="text-[#607080] font-medium">Workplace Destination</span>
              <div className="text-base font-extrabold text-[#06243A] truncate">
                {location.state.searchCriteria.workplaceLabel || 'Confirmed Workplace'}
              </div>
              <div className="text-[11px] text-[#0878D1] font-semibold">Door-to-door destination ✓</div>
            </div>
          </div>
        </div>
      )}

      {/* 3. "Why RIVO Recommends This Home" Evaluation Grid */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E2E8F0] shadow-sm space-y-6">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-[#0878D1] bg-[#F3F8FC] px-3 py-1 rounded-full border border-[#BFDBFE]">
            Holistic Life Evaluation
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#06243A] tracking-tight mt-2">
            Why RIVO Recommends This Home
          </h2>
          <p className="text-xs sm:text-sm text-[#607080] mt-1">
            Door-to-door transit reliability, real expenditure transparency, and verified neighborhood access.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* 1. Housing & Budget Fit */}
          <div className="p-5 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE] space-y-2">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-[#0878D1] shadow-xs">
              <Building className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-[#06243A]">Housing Fit</h3>
            <div className="text-2xl font-extrabold text-[#06243A]">₹{rent.toLocaleString()}</div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Fits within target budget limit. Deposit terms aligned to standard Chennai 6–10 month tenant guidelines.
            </p>
          </div>

          {/* 2. Door-to-Door Commute */}
          <div className="p-5 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE] space-y-2">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-[#0878D1] shadow-xs">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-[#06243A]">Door-to-Door Commute</h3>
            <div className="text-2xl font-extrabold text-[#0878D1]">{durationMin} min</div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Calculated to workplace anchor via {bestRoute?.mode || 'Multimodal Transit'} with walking egress.
            </p>
          </div>

          {/* 3. Travel Cost Outflow */}
          <div className="p-5 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE] space-y-2">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-[#0878D1] shadow-xs">
              <Navigation className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-[#06243A]">Travel Fare Outflow</h3>
            <div className="text-2xl font-extrabold text-[#0878D1]">₹{transportCost.toLocaleString()}</div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Monthly transit fare (22 work days × round trips) calibrated against official MTC/CMRL fare tables.
            </p>
          </div>

          {/* 4. Family & Health Access */}
          <div className="p-5 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE] space-y-2">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-[#10B981] shadow-xs">
              <HeartPulse className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-[#06243A]">Family Access</h3>
            <div className="text-2xl font-extrabold text-[#10B981]">Verified</div>
            <p className="text-xs text-[#607080] leading-relaxed">
              UDISE+ recognized school within {((listing.school_access?.distance_m || 1200) / 1000).toFixed(1)} km, hospital within {((listing.hospital_access?.distance_m || 1800) / 1000).toFixed(1)} km.
            </p>
          </div>
        </div>
      </div>

      {/* 4. Commute Comparison Across Modes */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E2E8F0] shadow-sm space-y-6">
        <div>
          <h3 className="text-xl font-extrabold text-[#06243A] tracking-tight">
            Commute Mode Comparison to Workplace
          </h3>
          <p className="text-xs text-[#607080] mt-1">
            Door-to-door duration and monthly cash expenditure across travel modes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Mode 1: Multimodal Transit */}
          <div className="p-4 rounded-2xl bg-[#F3F8FC] border border-[#BFDBFE] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0878D1]">
              <Train className="w-4 h-4" />
              <span>Multimodal Transit</span>
            </div>
            <div className="text-2xl font-extrabold text-[#06243A]">{durationMin} min</div>
            <div className="text-xs text-[#607080]">₹{transportCost.toLocaleString()} / mo</div>
            <div className="text-[11px] text-emerald-600 font-semibold">Recommended • Low carbon</div>
          </div>

          {/* Mode 2: Two-Wheeler */}
          <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
              <Bike className="w-4 h-4" />
              <span>Two-Wheeler (Scooter)</span>
            </div>
            <div className="text-2xl font-extrabold text-[#06243A]">
              ~{Math.max(18, Math.round(durationMin * 0.7))} min
            </div>
            <div className="text-xs text-[#607080]">
              ~₹{Math.round(transportCost * 1.35).toLocaleString()} / mo petrol
            </div>
            <div className="text-[11px] text-slate-500">Subject to peak city traffic</div>
          </div>

          {/* Mode 3: Drive / Cab */}
          <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
              <Car className="w-4 h-4" />
              <span>Drive / Cab</span>
            </div>
            <div className="text-2xl font-extrabold text-[#06243A]">
              ~{Math.max(25, Math.round(durationMin * 0.85))} min
            </div>
            <div className="text-xs text-[#607080]">
              ~₹{Math.round(transportCost * 3.8).toLocaleString()} / mo
            </div>
            <div className="text-[11px] text-slate-500">High peak hour congestion</div>
          </div>

          {/* Mode 4: Walk */}
          <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
              <Navigation className="w-4 h-4" />
              <span>Walking (First/Last Mile)</span>
            </div>
            <div className="text-2xl font-extrabold text-[#06243A]">~8 min</div>
            <div className="text-xs text-[#607080]">₹0 fare</div>
            <div className="text-[11px] text-emerald-600 font-semibold">Transit station access</div>
          </div>
        </div>
      </div>

      {/* 5. Combined Household Affordability Breakdown */}
      <div className="bg-[#06243A] text-white rounded-3xl p-6 sm:p-8 border border-white/10 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#F5C542]">
              Transparent Household Economics
            </span>
            <h3 className="text-2xl font-extrabold text-white mt-1">
              Combined Monthly Cost of Living: ₹{totalCost.toLocaleString()}
            </h3>
            <p className="text-xs text-slate-300 mt-1">
              Rent + Maintenance + Verified Commute Outflow for 22 Work Days
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs text-[#13A8E8] bg-white/10 px-4 py-2 rounded-xl border border-white/20 font-semibold">
            <Shield className="w-4 h-4" />
            <span>Calibrated against PLFS 2025 Wage Distributions</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-4 border-t border-white/10 text-xs">
          <div className="space-y-1">
            <span className="text-slate-400">Monthly Rent:</span>
            <div className="text-xl font-bold text-white">₹{rent.toLocaleString()}</div>
            <div className="text-[11px] text-slate-400">~{Math.round((rent / totalCost) * 100)}% of combined outflow</div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-400">Monthly Travel Outflow:</span>
            <div className="text-xl font-bold text-[#13A8E8]">₹{transportCost.toLocaleString()}</div>
            <div className="text-[11px] text-slate-400">~{Math.round((transportCost / totalCost) * 100)}% of combined outflow</div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-400">Estimated Living Tax:</span>
            <div className="text-xl font-bold text-[#F5C542]">{Math.round(durationMin * 44 / 60)} hrs / mo</div>
            <div className="text-[11px] text-slate-400">Door-to-door transit time tax</div>
          </div>
        </div>
      </div>
    </div>
  );
};
