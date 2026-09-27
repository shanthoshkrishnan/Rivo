import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Clock,
  Navigation,
  School,
  HeartPulse,
  Pill,
  CheckCircle2,
  ChevronRight,
  Camera,
  Train,
  Bike,
  Car,
  AlertTriangle,
  Bus,
} from 'lucide-react';
import { RecommendationResult, RouteResult } from '../../types/api';
import { getPropertyImages, getFallbackImage } from '../../utils/propertyImages';

export interface SearchCriteriaContext {
  workplaceLabel?: string;
  minRent?: number;
  maxRent?: number;
  bhk?: number;
  maxCommuteMinutes?: number;
  selectedTravelMode?: 'TRANSIT' | 'TWO_WHEELER' | 'DRIVE' | 'WALK';
  householdIncome?: number;
  schoolMaxMin?: number;
  hospitalMaxMin?: number;
  pharmacyMaxMin?: number;
}

interface ListingCardProps {
  listing: RecommendationResult;
  isSelected: boolean;
  searchCriteria?: SearchCriteriaContext;
  onSelect: (listing: RecommendationResult) => void;
  onHover?: (listingId: string | null) => void;
  onViewRouteModal?: (listing: RecommendationResult) => void;
}

function formatDistance(m?: number): string {
  if (m === undefined || m === null) return '—';
  if (m < 1000) return `${Math.round(m)} m`;
  return `${(m / 1000).toFixed(1)} km`;
}

export const ListingCard: React.FC<ListingCardProps> = ({
  listing,
  isSelected,
  searchCriteria,
  onSelect,
  onHover,
}) => {
  const rent = listing.rent_monthly || 0;
  const maintenance = listing.maintenance_monthly || 0;
  const deposit = listing.deposit;

  // Active route based on selected travel mode or best route fallback
  const activeMode = searchCriteria?.selectedTravelMode || 'TRANSIT';
  const modeRoute =
    listing.all_routes?.find((r) => r.mode === activeMode) ||
    listing.best_route;

  const commuteMin = modeRoute?.duration_minutes ?? modeRoute?.duration_min ?? Math.round((modeRoute?.duration_seconds || 0) / 60);
  const distanceKm = modeRoute?.distance_km ?? (modeRoute?.distance_m ? +(modeRoute.distance_m / 1000).toFixed(1) : undefined);

  // Travel cost: prefer backend calculated monthly_commute_cost, otherwise compute
  let monthlyTransportCost = modeRoute?.monthly_commute_cost;
  if (monthlyTransportCost === undefined) {
    if (activeMode === 'TRANSIT') {
      const fare = modeRoute?.fare_amount ?? modeRoute?.fare_inr ?? 25;
      monthlyTransportCost = Math.round(fare * 2 * 22);
    } else if (activeMode === 'TWO_WHEELER') {
      const d = distanceKm ?? 10;
      monthlyTransportCost = Math.round(((d * 2 * 22) / 45) * 105);
    } else if (activeMode === 'DRIVE') {
      const d = distanceKm ?? 10;
      monthlyTransportCost = Math.round(((d * 2 * 22) / 14) * 105);
    } else {
      monthlyTransportCost = 0;
    }
  }

  // Facility access values
  const nf = listing.nearest_facilities || {};
  const schoolDistM = nf.school?.distance_m ?? listing.school_access?.distance_m;
  const hospDistM = nf.hospital?.distance_m ?? listing.hospital_access?.distance_m;
  const pharmDistM = nf.pharmacy?.distance_m ?? listing.pharmacy_access?.distance_m;
  const busDistM = nf.bus_stop?.distance_m;
  const metroDistM = nf.metro?.distance_m;

  const imageSet = getPropertyImages(listing.listing_id, listing.locality, listing.bhk);
  const [imgSrc, setImgSrc] = useState(imageSet.cover);

  // Search limits
  const maxCommute = searchCriteria?.maxCommuteMinutes ?? 45;
  const minRent = searchCriteria?.minRent;
  const maxRent = searchCriteria?.maxRent;
  const requestedBhk = searchCriteria?.bhk;
  const householdIncome = searchCriteria?.householdIncome;

  const rentFitsRange =
    minRent !== undefined && maxRent !== undefined
      ? rent >= minRent && rent <= maxRent
      : maxRent !== undefined
      ? rent <= maxRent
      : true;

  const commuteFits = commuteMin ? commuteMin <= maxCommute : true;
  const bhkFits = requestedBhk ? listing.bhk === requestedBhk : true;

  // Evidence bullets for "WHY THIS HOME"
  const evidenceBullets: { text: string; positive: boolean }[] = [];

  if (rentFitsRange) {
    evidenceBullets.push({
      text: minRent && maxRent ? `Rent ₹${rent.toLocaleString()} is inside ₹${minRent.toLocaleString()}–₹${maxRent.toLocaleString()} budget` : `Rent ₹${rent.toLocaleString()} is within budget limit`,
      positive: true,
    });
  } else if (maxRent && rent > maxRent) {
    evidenceBullets.push({
      text: `Rent ₹${rent.toLocaleString()} is above ₹${maxRent.toLocaleString()} budget`,
      positive: false,
    });
  }

  if (bhkFits) {
    evidenceBullets.push({
      text: `${listing.bhk || 2} BHK matches your requirement`,
      positive: true,
    });
  }

  if (commuteMin) {
    if (commuteFits) {
      evidenceBullets.push({
        text: `${commuteMin} min commute is within your ${maxCommute} min limit`,
        positive: true,
      });
    } else {
      evidenceBullets.push({
        text: `${commuteMin} min commute exceeds your ${maxCommute} min limit`,
        positive: false,
      });
    }
  }

  if (schoolDistM && schoolDistM <= 1500) {
    evidenceBullets.push({
      text: `School is ${formatDistance(schoolDistM)} away (${nf.school?.name || 'Local School'})`,
      positive: true,
    });
  }

  if (busDistM && busDistM <= 800) {
    evidenceBullets.push({
      text: `Bus stop is ${formatDistance(busDistM)} away (${nf.bus_stop?.name || 'MTC Stop'})`,
      positive: true,
    });
  }

  if (hospDistM && hospDistM > 2500) {
    evidenceBullets.push({
      text: `Hospital is ${formatDistance(hospDistM)} away`,
      positive: false,
    });
  }

  // Travel Mode Icons
  const ModeIcon =
    activeMode === 'TRANSIT'
      ? Train
      : activeMode === 'TWO_WHEELER'
      ? Bike
      : activeMode === 'DRIVE'
      ? Car
      : Navigation;

  return (
    <div
      onClick={() => onSelect(listing)}
      onMouseEnter={() => onHover?.(listing.listing_id)}
      onMouseLeave={() => onHover?.(null)}
      className={`group rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden bg-white ${
        isSelected
          ? 'border-[#0878D1] shadow-xl ring-2 ring-[#0878D1]/20 -translate-y-1'
          : 'border-[#E2E8F0] hover:border-[#0878D1]/50 hover:shadow-lg hover:-translate-y-1'
      }`}
    >
      {/* 1. Large High-Quality Visual */}
      <div className="relative h-48 sm:h-52 w-full bg-[#F3F8FC] overflow-hidden">
        <img
          src={imgSrc}
          alt={`${listing.bhk || 2} BHK in ${listing.locality || 'Chennai'}`}
          onError={() => setImgSrc(getFallbackImage(0))}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-104 transition-transform duration-500 ease-out"
        />

        {/* Clean Top Badges */}
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
          <span
            className={`text-[10px] font-bold px-2.5 py-1 rounded uppercase tracking-wider backdrop-blur-md shadow-xs ${
              listing.provider === 'rivo_direct'
                ? 'bg-[#059669] text-white'
                : 'bg-[#06243A]/90 text-white border border-white/20'
            }`}
          >
            {listing.provider === 'rivo_direct' ? 'Live Listing' : 'DEMO INVENTORY'}
          </span>

          <span className="inline-flex items-center space-x-1 text-[11px] font-medium px-2 py-0.5 rounded bg-black/60 text-white backdrop-blur-xs">
            <Camera className="w-3.5 h-3.5" />
            <span>{imageSet.gallery.length}</span>
          </span>
        </div>

        {/* Bottom Property Tag */}
        <div className="absolute bottom-3 left-3">
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded bg-black/65 text-white backdrop-blur-xs">
            {imageSet.propertyTypeLabel}
          </span>
        </div>
      </div>

      {/* 2. Main Body matching Requirement 37 */}
      <div className="p-4 sm:p-5 space-y-4">
        {/* Price & Overview */}
        <div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold tracking-tight text-[#06243A]">
              ₹{rent.toLocaleString()}
            </span>
            <span className="text-xs text-[#607080] font-normal">/ month</span>
            {maintenance > 0 && (
              <span className="text-[11px] text-[#607080] font-medium">
                + ₹{maintenance} maint.
              </span>
            )}
          </div>
          <div className="text-xs font-semibold text-[#607080] mt-1 flex flex-wrap items-center gap-1.5">
            <span className="text-[#06243A] font-bold">{listing.bhk || 2} BHK</span>
            <span>·</span>
            <span>{listing.area_sqft || 850} sq ft</span>
            <span>·</span>
            <span className="capitalize">{listing.locality || 'Chennai'}</span>
            {deposit && (
              <>
                <span>·</span>
                <span className="text-[#607080]">Deposit ₹{(deposit / 1000).toFixed(0)}k</span>
              </>
            )}
          </div>
          {listing.address && (
            <div className="text-[11px] text-[#607080] mt-0.5 truncate" title={listing.address}>
              {listing.address}
            </div>
          )}
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* YOUR COMMUTE (Door-to-Door Calculated Route) */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] p-3 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-bold text-[#607080] uppercase tracking-wider">
            <span>Your Commute</span>
            <span className="text-[10px] text-[#0878D1] font-semibold">
              {searchCriteria?.workplaceLabel || 'Workplace'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-sm font-extrabold text-[#06243A]">
              <ModeIcon className="w-4 h-4 text-[#0878D1]" />
              <span>{commuteMin || '—'} min</span>
              {distanceKm !== undefined && (
                <span className="text-xs font-medium text-[#607080]">· {distanceKm} km</span>
              )}
            </div>

            <div className="text-xs font-bold text-[#0878D1] bg-[#F3F8FC] px-2 py-0.5 rounded border border-[#BFDBFE]">
              {activeMode === 'WALK' ? '₹0 / mo' : `₹${monthlyTransportCost.toLocaleString()} / mo transport`}
            </div>
          </div>

          {/* Commute breakdown/transfers */}
          <div className="text-[11px] text-[#607080] flex items-center justify-between pt-1 border-t border-[#E2E8F0]/70">
            <span>
              {activeMode === 'TRANSIT'
                ? `${modeRoute?.transfers ?? modeRoute?.transfer_count ?? 1} transfer${(modeRoute?.transfers ?? 1) > 1 ? 's' : ''} (MTC / Metro)`
                : activeMode === 'TWO_WHEELER'
                ? 'Fuel est. @ 45 km/L (₹105/L)'
                : activeMode === 'DRIVE'
                ? 'Fuel est. @ 14 km/L (₹105/L)'
                : 'Pedestrian door-to-door'}
            </span>
            <span className="text-[10px] text-[#0878D1] font-medium">
              {modeRoute?.source_label || 'RIVO / GTFS Router'}
            </span>
          </div>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* NEARBY ESSENTIALS (Directly calculated from coordinates) */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="space-y-1.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#607080]">
            Nearby Essentials
          </div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
            <div className="flex items-center space-x-1.5 text-[#06243A] truncate" title={nf.school?.name}>
              <School className="w-3.5 h-3.5 text-[#0878D1] shrink-0" />
              <span className="truncate">School <b>{formatDistance(schoolDistM)}</b></span>
            </div>
            <div className="flex items-center space-x-1.5 text-[#06243A] truncate" title={nf.hospital?.name}>
              <HeartPulse className="w-3.5 h-3.5 text-[#EF4444] shrink-0" />
              <span className="truncate">Hospital <b>{formatDistance(hospDistM)}</b></span>
            </div>
            <div className="flex items-center space-x-1.5 text-[#06243A] truncate" title={nf.pharmacy?.name}>
              <Pill className="w-3.5 h-3.5 text-[#10B981] shrink-0" />
              <span className="truncate">Pharmacy <b>{formatDistance(pharmDistM)}</b></span>
            </div>
            <div className="flex items-center space-x-1.5 text-[#06243A] truncate" title={nf.bus_stop?.name}>
              <Bus className="w-3.5 h-3.5 text-[#E69900] shrink-0" />
              <span className="truncate">Bus Stop <b>{formatDistance(busDistM)}</b></span>
            </div>
          </div>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* WHY THIS HOME (Data-Driven Explainability Engine) */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="space-y-1.5 pt-2 border-t border-[#F1F5F9]">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#607080]">
            Why This Home
          </div>
          <ul className="space-y-1">
            {evidenceBullets.slice(0, 4).map((b, idx) => (
              <li
                key={idx}
                className="text-xs text-[#06243A] flex items-start space-x-1.5 leading-tight"
              >
                {b.positive ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981] shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-[#F59E0B] shrink-0 mt-0.5" />
                )}
                <span>{b.text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* Action Bar */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="pt-2 border-t border-[#F1F5F9] flex items-center justify-between">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(listing);
            }}
            className="px-3 py-2 rounded-xl bg-[#F3F8FC] hover:bg-[#EEF5FF] text-[#0878D1] border border-[#BFDBFE] text-xs font-bold transition-all cursor-pointer"
          >
            Highlight on Map
          </button>

          <Link
            to={`/property/${listing.listing_id}`}
            state={{ listing, searchCriteria }}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-[#0878D1] hover:bg-[#0764B0] text-white text-xs font-bold shadow-xs hover:shadow transition-all cursor-pointer"
          >
            <span>View Home</span>
            <ChevronRight className="w-3.5 h-3.5 text-[#F5C542]" />
          </Link>
        </div>
      </div>
    </div>
  );
};
