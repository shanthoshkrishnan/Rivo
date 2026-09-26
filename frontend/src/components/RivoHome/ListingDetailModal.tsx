import React from 'react';
import {
  X,
  Navigation,
  School,
  HeartPulse,
  Pill,
  Clock,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Shield,
  Layers,
  Fuel,
} from 'lucide-react';
import { RecommendationResult } from '../../types/api';

interface ListingDetailModalProps {
  listing: RecommendationResult | null;
  onClose: () => void;
}

export const ListingDetailModal: React.FC<ListingDetailModalProps> = ({
  listing,
  onClose,
}) => {
  if (!listing) return null;

  const rent = listing.rent_monthly || 0;
  const maintenance = listing.maintenance_monthly || 0;
  const transport = listing.affordability?.monthly_transport_cost || 0;
  const total = rent + maintenance + transport;
  const burdenPct = listing.affordability?.cash_burden_pct;
  const timeTaxHours = listing.affordability?.monthly_commute_hours;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/30 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="relative w-full max-w-2xl bg-white rounded-3xl border border-[#EBE4DC] shadow-xl overflow-hidden animate-fadeIn">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#EBE4DC] bg-[#FAF8F5]">
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xl font-bold text-[#2C2523]">
                ₹{rent.toLocaleString()}
                <span className="text-xs font-normal text-[#8C7E75]">/mo</span>
              </h3>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#EBF4EF] text-[#346647] border border-[#D0E5D8]">
                {listing.bhk || 2} BHK
              </span>
            </div>
            <p className="text-xs text-[#6B615B] mt-0.5">
              {listing.locality || 'Chennai'} • {listing.area_sqft || 850} sqft • {listing.property_type || 'flat'}
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-[#EFE8DF] hover:bg-[#E2D8CC] flex items-center justify-center text-[#554C47] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* Section 1: Multi-Mode Route Comparison */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-[#5A504B] uppercase tracking-wider">
                Door-to-Door Travel Comparison
              </h4>
              <span className="text-[11px] text-[#8C7E75]">CUMTA GTFS + Google / OTP model</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {listing.all_routes.length > 0 ? (
                listing.all_routes.map((rt, idx) => (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-xl border text-xs ${
                      rt.is_fastest
                        ? 'border-[#C25E38] bg-[#FAF5F0]'
                        : 'border-[#EBE4DC] bg-[#FAF8F5]/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center space-x-1.5 font-semibold text-[#2C2523] capitalize">
                        <Navigation className="w-3.5 h-3.5 text-[#C25E38]" />
                        <span>{rt.mode.replace('_', ' ')}</span>
                      </div>
                      <div className="flex space-x-1">
                        {rt.is_fastest && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#C25E38] text-white">
                            FASTEST
                          </span>
                        )}
                        {rt.is_cheapest && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#3E7353] text-white">
                            CHEAPEST
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-baseline justify-between mt-2 text-[#4A3E39]">
                      <div>
                        <span className="text-base font-bold">{Math.round(rt.duration_minutes)}</span>
                        <span className="text-[11px] text-[#8C7E75] ml-1">mins one-way</span>
                      </div>
                      <div className="font-semibold text-right">
                        {rt.fare_inr ? `₹${rt.fare_inr}` : 'Est. fuel'}
                      </div>
                    </div>

                    {rt.transfers > 0 && (
                      <div className="text-[10px] text-[#8C7E75] mt-1">
                        {rt.transfers} transit transfer{rt.transfers > 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#EBE4DC] text-xs text-[#7A6F68]">
                  Transit: ~{Math.round(listing.best_route?.duration_minutes || 35)} min (Metro / MTC Bus)
                </div>
              )}
            </div>
          </div>

          {/* Section 2: Real Monthly Living Cost Breakdown (ALGORITHMS.md) */}
          <div className="p-4 rounded-2xl bg-[#FAF8F5] border border-[#EDE5DC] space-y-3">
            <h4 className="text-xs font-bold text-[#5A504B] uppercase tracking-wider">
              Total Monthly Housing + Transport (H+T) Burden
            </h4>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
              <div className="p-2.5 bg-white rounded-xl border border-[#EBE4DC]">
                <div className="text-[10px] text-[#8C7E75]">Rent</div>
                <div className="font-bold text-[#2C2523] mt-0.5">₹{rent.toLocaleString()}</div>
              </div>
              <div className="p-2.5 bg-white rounded-xl border border-[#EBE4DC]">
                <div className="text-[10px] text-[#8C7E75]">Maintenance</div>
                <div className="font-bold text-[#2C2523] mt-0.5">₹{maintenance.toLocaleString()}</div>
              </div>
              <div className="p-2.5 bg-white rounded-xl border border-[#EBE4DC]">
                <div className="text-[10px] text-[#8C7E75]">Monthly Transit</div>
                <div className="font-bold text-[#C25E38] mt-0.5">₹{transport.toLocaleString()}</div>
              </div>
              <div className="p-2.5 bg-white rounded-xl border border-[#C25E38]/30">
                <div className="text-[10px] text-[#8C7E75]">Total Monthly</div>
                <div className="font-bold text-[#C25E38] mt-0.5">₹{total.toLocaleString()}</div>
              </div>
            </div>

            {burdenPct != null && (
              <div className="pt-2 text-xs text-[#6B615B] flex items-center justify-between border-t border-[#EDE5DC]">
                <span>
                  Estimated Income Burden:{' '}
                  <b className={burdenPct > 45 ? 'text-[#B83A2E]' : 'text-[#3E7353]'}>
                    {burdenPct.toFixed(1)}%
                  </b>{' '}
                  of household earnings
                </span>
                {timeTaxHours != null && (
                  <span>
                    Monthly Time Tax: <b>{timeTaxHours.toFixed(1)} hrs</b>
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Section 3: Family Accessibility Proximity */}
          <div>
            <h4 className="text-xs font-bold text-[#5A504B] uppercase tracking-wider mb-2">
              Family Proximity
            </h4>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-xl border border-[#EBE4DC] bg-white">
                <div className="flex items-center space-x-1.5 text-[#C25E38] font-semibold mb-1">
                  <School className="w-3.5 h-3.5" />
                  <span>School</span>
                </div>
                <div className="text-sm font-bold text-[#2C2523]">
                  {listing.school_access?.nearest_minutes ? `${Math.round(listing.school_access.nearest_minutes)}m` : '8m'}
                </div>
                <div className="text-[10px] text-[#8C7E75]">UDISE+ Registered</div>
              </div>

              <div className="p-3 rounded-xl border border-[#EBE4DC] bg-white">
                <div className="flex items-center space-x-1.5 text-[#C25E38] font-semibold mb-1">
                  <HeartPulse className="w-3.5 h-3.5" />
                  <span>Hospital</span>
                </div>
                <div className="text-sm font-bold text-[#2C2523]">
                  {listing.hospital_access?.nearest_minutes ? `${Math.round(listing.hospital_access.nearest_minutes)}m` : '14m'}
                </div>
                <div className="text-[10px] text-[#8C7E75]">Chennai OGD</div>
              </div>

              <div className="p-3 rounded-xl border border-[#EBE4DC] bg-white">
                <div className="flex items-center space-x-1.5 text-[#C25E38] font-semibold mb-1">
                  <Pill className="w-3.5 h-3.5" />
                  <span>Pharmacy</span>
                </div>
                <div className="text-sm font-bold text-[#2C2523]">
                  {listing.pharmacy_access?.nearest_minutes ? `${Math.round(listing.pharmacy_access.nearest_minutes)}m` : '5m'}
                </div>
                <div className="text-[10px] text-[#8C7E75]">OSM Chennai POI</div>
              </div>
            </div>
          </div>

          {/* Section 4: Data Provenance & Freshness */}
          <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#EBE4DC] text-[11px] text-[#8C7E75] flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="w-3.5 h-3.5 text-[#A69C95]" />
              <span>
                Freshness: <b className="text-[#2C2523]">{listing.data_freshness}</b> • Provider:{' '}
                <b className="text-[#2C2523]">{listing.provider}</b>
              </span>
            </div>
            <span>ID: {listing.listing_id}</span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#EBE4DC] bg-[#FAF8F5] flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-[#2C2523] hover:bg-[#433A36] text-white text-xs font-semibold cursor-pointer"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
