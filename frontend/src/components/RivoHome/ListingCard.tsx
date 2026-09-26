import React from 'react';
import {
  Clock,
  Navigation,
  School,
  HeartPulse,
  Pill,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { RecommendationResult } from '../../types/api';

interface ListingCardProps {
  listing: RecommendationResult;
  isSelected: boolean;
  onSelect: (listing: RecommendationResult) => void;
  onViewRouteModal: (listing: RecommendationResult) => void;
}

export const ListingCard: React.FC<ListingCardProps> = ({
  listing,
  isSelected,
  onSelect,
  onViewRouteModal,
}) => {
  const rent = listing.rent_monthly || 0;
  const maintenance = listing.maintenance_monthly || 0;
  const transportCost = listing.affordability?.monthly_transport_cost || 0;
  const totalMonthlyCost = rent + maintenance + transportCost;

  const bestRoute = listing.best_route;
  const whyReasons = listing.explainability?.positive_reasons || [];
  const whyNegative = listing.explainability?.negative_reasons || [];
  const confidence = listing.explainability?.confidence || 'MEDIUM';

  return (
    <div
      onClick={() => onSelect(listing)}
      className={`rounded-2xl p-5 border transition-all duration-200 cursor-pointer ${
        isSelected
          ? 'bg-white border-[#C25E38] shadow-md ring-1 ring-[#C25E38]'
          : 'bg-white border-[#EBE4DC] hover:border-[#D6CBC0] hover:shadow-sm'
      }`}
    >
      {/* Top row: Price, BHK, Freshness */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-baseline space-x-2">
            <span className="text-xl font-bold tracking-tight text-[#2C2523]">
              ₹{rent.toLocaleString()}
            </span>
            <span className="text-xs text-[#8C7E75]">/month</span>
          </div>
          <div className="text-xs font-medium text-[#6B615B] mt-0.5">
            {listing.bhk ? `${listing.bhk} BHK • ` : ''}
            {listing.area_sqft ? `${listing.area_sqft} sqft • ` : ''}
            <span className="capitalize">{listing.locality || 'Chennai'}</span>
          </div>
        </div>

        <div className="flex flex-col items-end space-y-1">
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${
              confidence === 'HIGH'
                ? 'bg-[#EBF4EF] text-[#346647] border border-[#D0E5D8]'
                : 'bg-[#FDF6EC] text-[#9E641F] border border-[#F3E2C8]'
            }`}
          >
            {confidence} CONFIDENCE
          </span>
          <span className="text-[10px] text-[#A69C95] bg-[#F7F3EE] px-1.5 py-0.5 rounded font-mono">
            {listing.data_freshness}
          </span>
        </div>
      </div>

      {/* Best Commute Pill */}
      {bestRoute && (
        <div className="mb-3 p-2.5 rounded-xl bg-[#FAF8F5] border border-[#EDE5DC] flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-lg bg-[#EFE8DF] flex items-center justify-center text-[#C25E38]">
              <Navigation className="w-3.5 h-3.5" />
            </div>
            <div>
              <span className="font-semibold text-[#2C2523] capitalize">
                {bestRoute.mode.replace('_', ' ')}
              </span>
              <span className="text-[#8C7E75] ml-1.5">
                • {Math.round(bestRoute.duration_minutes)} min
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="font-semibold text-[#4A3E39]">
              {bestRoute.fare_inr ? `₹${bestRoute.fare_inr}` : '₹0'}
            </span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onViewRouteModal(listing);
              }}
              className="text-[11px] text-[#C25E38] hover:underline font-medium"
            >
              Compare
            </button>
          </div>
        </div>
      )}

      {/* Monthly Real Living Burden (Rent + Maintenance + Commute) */}
      <div className="grid grid-cols-3 gap-2 py-2 mb-3 border-y border-[#F3EDE6] text-center text-xs">
        <div>
          <div className="text-[10px] text-[#9E938D] uppercase tracking-wider">Rent</div>
          <div className="font-semibold text-[#2C2523]">₹{rent.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-[10px] text-[#9E938D] uppercase tracking-wider">Maint.</div>
          <div className="font-semibold text-[#2C2523]">₹{maintenance.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-[10px] text-[#9E938D] uppercase tracking-wider">Transport</div>
          <div className="font-semibold text-[#C25E38]">₹{transportCost.toLocaleString()}</div>
        </div>
      </div>

      {/* Family Access Times */}
      <div className="flex items-center justify-between text-xs text-[#6B615B] mb-3 px-1">
        <div className="flex items-center space-x-1" title="Nearest school">
          <School className="w-3.5 h-3.5 text-[#8C7E75]" />
          <span>{listing.school_access?.nearest_minutes ? `${Math.round(listing.school_access.nearest_minutes)}m` : '8m'}</span>
        </div>
        <div className="flex items-center space-x-1" title="Nearest hospital">
          <HeartPulse className="w-3.5 h-3.5 text-[#8C7E75]" />
          <span>{listing.hospital_access?.nearest_minutes ? `${Math.round(listing.hospital_access.nearest_minutes)}m` : '14m'}</span>
        </div>
        <div className="flex items-center space-x-1" title="Nearest pharmacy">
          <Pill className="w-3.5 h-3.5 text-[#8C7E75]" />
          <span>{listing.pharmacy_access?.nearest_minutes ? `${Math.round(listing.pharmacy_access.nearest_minutes)}m` : '5m'}</span>
        </div>
      </div>

      {/* Why RIVO explainability block */}
      <div className="pt-2 border-t border-[#F3EDE6] space-y-1">
        <div className="text-[10px] uppercase font-bold text-[#8C7E75] tracking-wider mb-1">
          Why RIVO Recommends This
        </div>
        {whyReasons.slice(0, 3).map((reason, idx) => (
          <div key={idx} className="flex items-center space-x-1.5 text-xs text-[#3E7353]">
            <CheckCircle2 className="w-3 h-3 text-[#3E7353] shrink-0" />
            <span className="capitalize">{reason.replace(/_/g, ' ')}</span>
          </div>
        ))}
        {whyNegative.length > 0 && (
          <div className="flex items-center space-x-1.5 text-xs text-[#B83A2E]">
            <AlertCircle className="w-3 h-3 text-[#B83A2E] shrink-0" />
            <span className="capitalize">{whyNegative[0].replace(/_/g, ' ')}</span>
          </div>
        )}
      </div>

      {/* Inspect button */}
      <div className="mt-3 pt-2 flex items-center justify-between text-xs text-[#C25E38] font-semibold">
        <span>Total H+T Monthly: ₹{totalMonthlyCost.toLocaleString()}</span>
        <div className="flex items-center space-x-1">
          <span>Details</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </div>
      </div>
    </div>
  );
};
