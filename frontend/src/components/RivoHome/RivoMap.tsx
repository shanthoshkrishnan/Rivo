import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { RecommendationResult } from '../../types/api';

interface RivoMapProps {
  workplace: { lat: number; lon: number; label: string };
  searchRadiusKm: number;
  listings: RecommendationResult[];
  selectedListingId: string | null;
  onSelectListing: (listing: RecommendationResult) => void;
}

export const RivoMap: React.FC<RivoMapProps> = ({
  workplace,
  searchRadiusKm,
  listings,
  selectedListingId,
  onSelectListing,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Center on Chennai
    const map = L.map(mapContainerRef.current, {
      center: [workplace.lat, workplace.lon],
      zoom: 12,
      zoomControl: false,
    });

    // Add minimal warm Carto Positron basemap (soft, uncluttered, no bright blue ocean)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    // Zoom control on bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Markers & Layers when workplace, radius, or listings change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // 1. Search radius circle
    const circle = L.circle([workplace.lat, workplace.lon], {
      radius: searchRadiusKm * 1000,
      color: '#C25E38',
      weight: 1.5,
      opacity: 0.5,
      fillColor: '#EBE2D8',
      fillOpacity: 0.15,
      dashArray: '4, 4',
    });
    layerGroup.addLayer(circle);

    // 2. Workplace Marker
    const workplaceIcon = L.divIcon({
      className: 'custom-workplace-icon',
      html: `
        <div style="
          width: 32px;
          height: 32px;
          background: #2C2523;
          border: 2.5px solid #FFFFFF;
          border-radius: 50%;
          box-shadow: 0 4px 12px rgba(44, 37, 35, 0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 14px;
        ">
          🏢
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });

    const workplaceMarker = L.marker([workplace.lat, workplace.lon], { icon: workplaceIcon });
    workplaceMarker.bindPopup(`
      <div style="font-family: inherit;">
        <span style="font-size: 11px; text-transform: uppercase; font-weight: 600; color: #8C7E75; letter-spacing: 0.5px;">Workplace Destination</span>
        <h4 style="margin: 2px 0 0 0; font-size: 14px; font-weight: 700; color: #2C2523;">${workplace.label}</h4>
      </div>
    `);
    layerGroup.addLayer(workplaceMarker);

    // 3. Rental Listing Markers
    const bounds = L.latLngBounds([ [workplace.lat, workplace.lon] ]);

    listings.forEach((item) => {
      if (item.latitude == null || item.longitude == null) return;

      bounds.extend([item.latitude, item.longitude]);
      const isSelected = item.listing_id === selectedListingId;
      const rentFmt = item.rent_monthly ? `₹${(item.rent_monthly / 1000).toFixed(1)}k` : '₹--';
      const durationFmt = item.best_route?.duration_minutes ? `${Math.round(item.best_route.duration_minutes)}m` : '';

      const listingIcon = L.divIcon({
        className: 'custom-listing-icon',
        html: `
          <div style="
            background: ${isSelected ? '#C25E38' : '#FFFFFF'};
            color: ${isSelected ? '#FFFFFF' : '#2C2523'};
            border: 2px solid ${isSelected ? '#943F20' : '#D9CEBF'};
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            box-shadow: 0 3px 10px rgba(44, 37, 35, ${isSelected ? '0.28' : '0.12'});
            white-space: nowrap;
            transition: transform 0.15s ease;
            transform: ${isSelected ? 'scale(1.15)' : 'scale(1)'};
          ">
            <span>${rentFmt}</span>
            ${durationFmt ? `<span style="opacity: 0.7; font-size: 10px; font-weight: 500;">• ${durationFmt}</span>` : ''}
          </div>
        `,
        iconSize: [64, 28],
        iconAnchor: [32, 14],
      });

      const marker = L.marker([item.latitude, item.longitude], { icon: listingIcon });

      marker.on('click', () => {
        onSelectListing(item);
      });

      marker.bindPopup(`
        <div style="min-width: 180px; font-family: inherit;">
          <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-size: 11px; text-transform: uppercase; font-weight: 600; color: #8C7E75;">${item.locality || 'Chennai'}</span>
            <span style="font-size: 14px; font-weight: 700; color: #C25E38;">₹${(item.rent_monthly || 0).toLocaleString()}</span>
          </div>
          <div style="font-size: 12px; color: #6E645E; margin-bottom: 8px;">
            ${item.bhk ? `${item.bhk} BHK • ` : ''}${item.area_sqft ? `${item.area_sqft} sqft` : 'Residential'}
          </div>
          ${
            item.best_route
              ? `<div style="background: #F7F3EE; padding: 6px 8px; border-radius: 6px; font-size: 11px; color: #4A3E39; margin-bottom: 8px;">
                  🚀 <b>${item.best_route.mode}</b>: ~${Math.round(item.best_route.duration_minutes)} min (${item.best_route.fare_inr ? `₹${item.best_route.fare_inr}` : 'Fare ₹0'})
                </div>`
              : ''
          }
          <div style="font-size: 11px; color: #8C7E75; text-align: right;">Click card to inspect full door-to-door route</div>
        </div>
      `);

      layerGroup.addLayer(marker);
    });

    if (listings.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    } else {
      map.setView([workplace.lat, workplace.lon], 12);
    }
  }, [workplace, searchRadiusKm, listings, selectedListingId]);

  return (
    <div className="relative w-full h-full min-h-[380px] lg:min-h-[500px] rounded-2xl overflow-hidden border border-[#EBE4DC] shadow-sm bg-[#F5EFEB]">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating map badge / legend */}
      <div className="absolute top-3 left-3 z-[1000] bg-white/95 backdrop-blur-sm px-3 py-2 rounded-xl border border-[#EBE4DC] shadow-sm text-xs space-y-1">
        <div className="flex items-center space-x-2 text-[#4A3E39]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#2C2523]" />
          <span className="font-medium">Workplace ({workplace.label})</span>
        </div>
        <div className="flex items-center space-x-2 text-[#4A3E39]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#C25E38]" />
          <span>Rental Homes ({listings.length})</span>
        </div>
      </div>
    </div>
  );
};
