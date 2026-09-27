import React, { useState } from 'react';
import {
  X,
  Navigation,
  School,
  HeartPulse,
  Pill,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
} from 'lucide-react';
import { RecommendationResult } from '../../types/api';
import { getPropertyImages, getFallbackImage } from '../../utils/propertyImages';

interface ListingDetailModalProps {
  listing: RecommendationResult | null;
  onClose: () => void;
}

export const ListingDetailModal: React.FC<ListingDetailModalProps> = ({
  listing,
  onClose,
}) => {
  const [activePhotoIdx, setActivePhotoIdx] = useState(0);

  if (!listing) return null;

  const rent = listing.rent_monthly || 0;
  const maintenance = listing.maintenance_monthly || 0;
  const transport = listing.affordability?.monthly_transport_cost || 0;
  const total = rent + maintenance + transport;
  const housingBurden = listing.affordability?.housing_burden_pct;
  const cashBurden = listing.affordability?.cash_burden_pct;
  const timeTaxHours = listing.affordability?.monthly_commute_hours;

  const imageSet = getPropertyImages(listing.listing_id, listing.locality, listing.bhk);

  const bestRoute = listing.best_route;
  const allRoutes = listing.all_routes || [];
  const whyReasons = listing.explainability?.positive_reasons || [];
  const whyNegative = listing.explainability?.negative_reasons || [];
  const confidence = listing.explainability?.confidence || 'MEDIUM';

  const nextPhoto = () => {
    setActivePhotoIdx((prev) => (prev < imageSet.gallery.length - 1 ? prev + 1 : 0));
  };
  const prevPhoto = () => {
    setActivePhotoIdx((prev) => (prev > 0 ? prev - 1 : imageSet.gallery.length - 1));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#0B1F3A]/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl border border-[#CBD5E1] shadow-2xl overflow-hidden animate-fadeIn max-h-[92vh] flex flex-col">
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between p-4 px-6 border-b border-[#E2E8F0] bg-[#F8FAFC]">
          <div className="flex items-center space-x-2.5">
            <span
              className={`text-[10px] font-bold px-2.5 py-1 rounded uppercase tracking-wider ${
                listing.provider === 'rivo_direct'
                  ? 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]'
                  : 'bg-[#F1F5F9] text-[#475569] border border-[#CBD5E1]'
              }`}
            >
              {listing.provider === 'rivo_direct' ? 'Live Listing' : 'Demo Inventory'}
            </span>
            <span className="text-xs text-[#607080]">
              ID: <code className="font-mono text-[11px] text-[#102033]">{listing.listing_id}</code>
            </span>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white hover:bg-[#F1F5F9] flex items-center justify-center text-[#607080] hover:text-[#102033] border border-[#E2E8F0] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Modal Body */}
        <div className="overflow-y-auto p-5 sm:p-7 space-y-6">
          {/* 1. Large Photo Gallery */}
          <div className="relative h-64 sm:h-80 w-full rounded-xl overflow-hidden bg-[#F4F8FC]">
            <img
              src={imageSet.gallery[activePhotoIdx] || imageSet.cover}
              alt={`${listing.bhk || 2} BHK in ${listing.locality || 'Chennai'}`}
              onError={(e) => {
                (e.target as HTMLImageElement).src = getFallbackImage(activePhotoIdx);
              }}
              className="w-full h-full object-cover transition-opacity duration-300"
            />

            {/* Gallery Navigation Arrows */}
            {imageSet.gallery.length > 1 && (
              <>
                <button
                  type="button"
                  onClick={prevPhoto}
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={nextPhoto}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </>
            )}

            {/* Bottom Photo Counter & Thumbnail Strip */}
            <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
              <span className="text-[11px] font-semibold px-2.5 py-1 rounded bg-black/65 text-white backdrop-blur-xs">
                Photo {activePhotoIdx + 1} of {imageSet.gallery.length} • {imageSet.propertyTypeLabel}
              </span>

              <div className="flex space-x-1.5">
                {imageSet.gallery.map((_, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setActivePhotoIdx(idx)}
                    className={`w-2 h-2 rounded-full transition-all ${
                      activePhotoIdx === idx ? 'bg-white scale-125' : 'bg-white/50'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* 2. Title, Price, Location */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-[#E2E8F0]">
            <div>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold tracking-tight text-[#102033]">
                  ₹{rent.toLocaleString()}
                </span>
                <span className="text-sm text-[#607080]">/ month</span>
                {maintenance > 0 && (
                  <span className="text-xs text-[#607080]">
                    (+ ₹{maintenance.toLocaleString()} maintenance)
                  </span>
                )}
              </div>
              <p className="text-sm font-semibold text-[#607080] mt-1 flex items-center space-x-2">
                <span className="text-[#102033] font-bold">{listing.bhk || 2} BHK {listing.property_type || 'Apartment'}</span>
                <span>•</span>
                <span className="capitalize">{listing.locality || 'Chennai'}</span>
                {listing.area_sqft && (
                  <>
                    <span>•</span>
                    <span>{listing.area_sqft} sq ft</span>
                  </>
                )}
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <span
                className={`text-xs font-bold px-3 py-1 rounded uppercase tracking-wider ${
                  (listing.availability_status || 'AVAILABLE') === 'AVAILABLE'
                    ? 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]'
                    : 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]'
                }`}
              >
                {listing.availability_status || 'AVAILABLE'}
              </span>
              <span className="text-xs font-semibold px-2.5 py-1 rounded bg-[#F8FAFC] text-[#607080] border border-[#E2E8F0]">
                Confidence: {confidence}
              </span>
            </div>
          </div>

          {/* 3. True Cost & Affordability Breakdown */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-[#102033] uppercase tracking-wider">
              True Household Affordability Breakdown
            </h4>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center">
                <div className="text-[10px] text-[#607080] font-semibold">Monthly Rent</div>
                <div className="text-base font-extrabold text-[#102033] mt-0.5">₹{rent.toLocaleString()}</div>
                <div className="text-[10px] text-[#059669] font-medium mt-0.5">
                  {housingBurden ? `${housingBurden}% income` : 'Standard'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center">
                <div className="text-[10px] text-[#607080] font-semibold">Monthly Transport</div>
                <div className="text-base font-extrabold text-[#1261D6] mt-0.5">₹{transport.toLocaleString()}</div>
                <div className="text-[10px] text-[#607080] font-medium mt-0.5">
                  {bestRoute?.mode?.toLowerCase()?.replace('_', ' ') || 'Transit'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center">
                <div className="text-[10px] text-[#607080] font-semibold">Total Cash Outflow</div>
                <div className="text-base font-extrabold text-[#102033] mt-0.5">₹{total.toLocaleString()}</div>
                <div className="text-[10px] text-[#1261D6] font-bold mt-0.5">
                  {cashBurden ? `${cashBurden}% total` : 'Rent + Travel'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center">
                <div className="text-[10px] text-[#607080] font-semibold">Commute Time Tax</div>
                <div className="text-base font-extrabold text-[#0B1F3A] mt-0.5">
                  {timeTaxHours ? `${timeTaxHours} hrs` : '~24 hrs'}
                </div>
                <div className="text-[10px] text-[#607080] font-medium mt-0.5">per month</div>
              </div>
            </div>
          </div>

          {/* 4. Multi-Mode Door-to-Door Route Comparison */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-[#102033] uppercase tracking-wider">
                Door-to-Door Travel to Workplace
              </h4>
              <span className="text-[11px] text-[#607080]">
                {bestRoute?.source_label || 'CUMTA GTFS + Google Routes Engine'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {allRoutes.length > 0 ? (
                allRoutes.map((rt, idx) => (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                      rt.is_fastest
                        ? 'border-[#1261D6] bg-[#F4F8FC]'
                        : 'border-[#E2E8F0] bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-1.5 font-bold text-[#102033] capitalize">
                        <Navigation className="w-3.5 h-3.5 text-[#1261D6]" />
                        <span>{rt.mode.replace('_', ' ')}</span>
                      </div>
                      {rt.is_fastest && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#1261D6] text-white">
                          FASTEST
                        </span>
                      )}
                      {rt.is_cheapest && !rt.is_fastest && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#059669] text-white">
                          CHEAPEST
                        </span>
                      )}
                    </div>

                    <div className="text-sm font-extrabold text-[#102033]">
                      {rt.duration_minutes ?? Math.round((rt.duration_seconds || 0) / 60)} min
                    </div>

                    <div className="text-[11px] text-[#607080] flex items-center justify-between">
                      <span>Fare / Fuel:</span>
                      <span className="font-semibold text-[#102033]">
                        {rt.fare_amount ? `₹${rt.fare_amount} / trip` : '₹0 (Walk)'}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-[#F8FAFC] text-xs text-[#607080] col-span-3 text-center">
                  Transit duration: ~{bestRoute?.duration_minutes || 35} mins door-to-door
                </div>
              )}
            </div>
          </div>

          {/* 5. Neighborhood & Family Essentials Access */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-[#102033] uppercase tracking-wider">
              Family &amp; Neighborhood Amenities
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* School */}
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-[#CBD5E1] flex items-center justify-center shrink-0">
                  <School className="w-4 h-4 text-[#1261D6]" />
                </div>
                <div>
                  <div className="text-[10px] text-[#607080] font-semibold">Primary / High School</div>
                  <div className="text-xs font-bold text-[#102033]">
                    {listing.school_access?.distance_m
                      ? `${(listing.school_access.distance_m / 1000).toFixed(1)} km (~${listing.school_access.nearest_minutes || 12} min walk)`
                      : 'Nearby School Available'}
                  </div>
                </div>
              </div>

              {/* Hospital */}
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-[#CBD5E1] flex items-center justify-center shrink-0">
                  <HeartPulse className="w-4 h-4 text-[#EF4444]" />
                </div>
                <div>
                  <div className="text-[10px] text-[#607080] font-semibold">Hospital / Clinic</div>
                  <div className="text-xs font-bold text-[#102033]">
                    {listing.hospital_access?.distance_m
                      ? `${(listing.hospital_access.distance_m / 1000).toFixed(1)} km (~${listing.hospital_access.nearest_minutes || 18} min walk)`
                      : 'Hospital Nearby'}
                  </div>
                </div>
              </div>

              {/* Pharmacy */}
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-[#CBD5E1] flex items-center justify-center shrink-0">
                  <Pill className="w-4 h-4 text-[#8B5CF6]" />
                </div>
                <div>
                  <div className="text-[10px] text-[#607080] font-semibold">Pharmacy</div>
                  <div className="text-xs font-bold text-[#102033]">
                    {listing.pharmacy_access?.distance_m
                      ? `${(listing.pharmacy_access.distance_m / 1000).toFixed(1)} km (~${listing.pharmacy_access.nearest_minutes || 6} min walk)`
                      : 'Pharmacy Within 500m'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 6. Why RIVO Recommends This */}
          <div className="p-5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#1261D6]">
              <CheckCircle2 className="w-4 h-4" />
              <span>Why This Home Fits Your Profile</span>
            </div>

            <ul className="space-y-1.5">
              {whyReasons.map((reason, idx) => (
                <li key={idx} className="text-xs text-[#102033] flex items-start space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#059669] shrink-0 mt-0.5" />
                  <span>{reason}</span>
                </li>
              ))}
            </ul>

            {whyNegative.length > 0 && (
              <div className="pt-2 border-t border-[#E2E8F0] space-y-1">
                <div className="text-[11px] font-bold text-[#607080]">Things to consider:</div>
                <ul className="space-y-1">
                  {whyNegative.map((item, idx) => (
                    <li key={idx} className="text-xs text-[#607080] flex items-start space-x-2">
                      <AlertCircle className="w-3.5 h-3.5 text-[#F7C948] shrink-0 mt-0.5" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 px-6 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between">
          <div className="text-[11px] text-[#607080]">
            Source: {listing.source_name || 'RIVO Seed Registry'} • Freshness: {listing.data_freshness}
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg bg-[#0B1F3A] hover:bg-[#162B4E] text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
