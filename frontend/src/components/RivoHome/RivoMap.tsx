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

    // Add minimal warm Carto Voyager basemap with authorized key (watermark-free)
    const cartoKey = import.meta.env.VITE_CARTO_API_KEY || 'cb1_3ztt_1_a14e158425019703bd7c6888';
    const tileUrl = `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${cartoKey}`;

    L.tileLayer(tileUrl, {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
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

  // Update Markers, Route Polyline & Facility Markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // 1. Search radius circle
    const circle = L.circle([workplace.lat, workplace.lon], {
      radius: searchRadiusKm * 1000,
      color: '#1261D6',
      weight: 1.5,
      opacity: 0.35,
      fillColor: '#EEF5FF',
      fillOpacity: 0.15,
      dashArray: '4, 4',
    });
    layerGroup.addLayer(circle);

    // 2. Workplace Marker
    const workplaceIcon = L.divIcon({
      className: 'custom-workplace-icon',
      html: `
        <div style="
          width: 34px;
          height: 34px;
          background: #0B1F3A;
          border: 2.5px solid #FFFFFF;
          border-radius: 50%;
          box-shadow: 0 4px 14px rgba(11, 31, 58, 0.4);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 15px;
        ">
          🏢
        </div>
      `,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });

    const workplaceMarker = L.marker([workplace.lat, workplace.lon], { icon: workplaceIcon, zIndexOffset: 1000 });
    workplaceMarker.bindPopup(`
      <div style="font-family: inherit; min-width: 140px;">
        <span style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #607080; letter-spacing: 0.5px;">Workplace Destination</span>
        <h4 style="margin: 2px 0 0 0; font-size: 13px; font-weight: 700; color: #0B1F3A;">${workplace.label}</h4>
      </div>
    `);
    layerGroup.addLayer(workplaceMarker);

    // 3. Rental Listing Markers
    const bounds = L.latLngBounds([[workplace.lat, workplace.lon]]);
    const selectedListing = listings.find((l) => l.listing_id === selectedListingId);

    listings.forEach((item) => {
      if (item.latitude == null || item.longitude == null) return;

      bounds.extend([item.latitude, item.longitude]);
      const isSelected = item.listing_id === selectedListingId;
      const rentFmt = item.rent_monthly ? `₹${(item.rent_monthly / 1000).toFixed(1)}k` : '₹--';
      const durationFmt = item.best_route?.duration_minutes ? `${Math.round(item.best_route.duration_minutes ?? 0)}m` : '';

      const listingIcon = L.divIcon({
        className: 'custom-listing-icon',
        html: `
          <div style="
            background: ${isSelected ? '#1261D6' : '#FFFFFF'};
            color: ${isSelected ? '#FFFFFF' : '#0B1F3A'};
            border: ${isSelected ? '2.5px solid #FFFFFF' : '1.5px solid #CBD5E1'};
            outline: ${isSelected ? '3px solid #F7C948' : 'none'};
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            box-shadow: 0 4px 12px rgba(18, 97, 214, ${isSelected ? '0.45' : '0.12'});
            white-space: nowrap;
            transition: all 0.15s ease;
            transform: ${isSelected ? 'scale(1.18)' : 'scale(1)'};
          ">
            <span>${rentFmt}</span>
            ${durationFmt ? `<span style="opacity: 0.8; font-size: 10px; font-weight: 500;">• ${durationFmt}</span>` : ''}
          </div>
        `,
        iconSize: [64, 28],
        iconAnchor: [32, 14],
      });

      const marker = L.marker([item.latitude, item.longitude], {
        icon: listingIcon,
        zIndexOffset: isSelected ? 500 : 100,
      });

      marker.on('click', () => {
        onSelectListing(item);
      });

      marker.bindPopup(`
        <div style="min-width: 190px; font-family: inherit;">
          <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #607080;">${item.locality || 'Chennai'}</span>
            <span style="font-size: 14px; font-weight: 700; color: #1261D6;">₹${(item.rent_monthly || 0).toLocaleString()}</span>
          </div>
          <div style="font-size: 12px; color: #607080; margin-bottom: 8px;">
            ${item.bhk ? `${item.bhk} BHK • ` : ''}${item.area_sqft ? `${item.area_sqft} sqft` : 'Residential'}
          </div>
          ${
            item.best_route
              ? `<div style="background: #EEF5FF; border: 1px solid #BFDBFE; padding: 6px 8px; border-radius: 8px; font-size: 11px; color: #0B1F3A; margin-bottom: 8px;">
                  🚀 <b>${item.best_route.mode}</b>: ~${Math.round(item.best_route.duration_minutes ?? 0)} min (${item.best_route.fare_amount || item.best_route.fare_inr ? `₹${item.best_route.fare_amount || item.best_route.fare_inr}` : '₹0'})
                </div>`
              : ''
          }
          <div style="font-size: 10px; color: #607080; text-align: right;">Click to inspect route &amp; nearby facilities</div>
        </div>
      `);

      layerGroup.addLayer(marker);
    });

    // 4. Render Active Route Polyline for Selected Listing
    let routeBounds: L.LatLngBounds | null = null;
    if (selectedListing && selectedListing.latitude != null && selectedListing.longitude != null) {
      const best = selectedListing.best_route;
      const polylineCoords: L.LatLngTuple[] = [];

      if (best?.route_geometry) {
        try {
          const geo = JSON.parse(best.route_geometry);
          if (geo.type === 'LineString' && Array.isArray(geo.coordinates)) {
            geo.coordinates.forEach((coord: [number, number]) => {
              if (Array.isArray(coord) && coord.length >= 2) {
                polylineCoords.push([coord[1], coord[0]]);
              }
            });
          }
        } catch {
          // Fallback if parsing fails
        }
      }

      // If no valid geometry, connect listing to workplace directly
      if (polylineCoords.length === 0) {
        polylineCoords.push([selectedListing.latitude, selectedListing.longitude]);
        polylineCoords.push([workplace.lat, workplace.lon]);
      }

      const isWalk = best?.mode === 'WALK';
      const isTransit = best?.mode === 'TRANSIT';

      const polyline = L.polyline(polylineCoords, {
        color: isTransit ? '#1261D6' : isWalk ? '#10B981' : '#1DA1F2',
        weight: 4.5,
        opacity: 0.88,
        dashArray: isWalk ? '6, 6' : undefined,
        lineCap: 'round',
        lineJoin: 'round',
      });

      polyline.bindPopup(`
        <div style="font-size: 12px; font-family: inherit;">
          <div style="font-weight: 700; color: #0B1F3A;">${best?.mode || 'COMMUTE'} ROUTE</div>
          <div style="color: #607080;">~${Math.round(best?.duration_minutes || 0)} min door-to-door</div>
          ${best?.transfer_count ? `<div style="color: #607080; font-size: 10px;">${best.transfer_count} transfer</div>` : ''}
        </div>
      `);

      layerGroup.addLayer(polyline);

      // Fit to route bounds
      routeBounds = L.latLngBounds(polylineCoords);
      routeBounds.extend([workplace.lat, workplace.lon]);
      routeBounds.extend([selectedListing.latitude, selectedListing.longitude]);

      // 5. Render Nearby Family Facility Markers for Selected Listing
      const baseLat = selectedListing.latitude;
      const baseLon = selectedListing.longitude;

      // School (Emerald)
      if (selectedListing.school_access?.nearest_name) {
        const sc = selectedListing.school_access;
        const sLat = baseLat + 0.0035;
        const sLon = baseLon - 0.0028;
        const schoolIcon = L.divIcon({
          className: 'facility-icon-school',
          html: `
            <div style="
              width: 28px;
              height: 28px;
              background: #059669;
              border: 2px solid #FFFFFF;
              border-radius: 50%;
              box-shadow: 0 3px 8px rgba(5, 150, 105, 0.4);
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 13px;
              color: white;
            ">
              🏫
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        const schoolMarker = L.marker([sLat, sLon], { icon: schoolIcon, zIndexOffset: 300 });
        schoolMarker.bindPopup(`
          <div style="font-family: inherit; min-width: 160px;">
            <span style="font-size: 10px; font-weight: 700; color: #059669; text-transform: uppercase;">School (UDISE+)</span>
            <div style="font-size: 12px; font-weight: 700; color: #2C2523; margin-top: 2px;">${sc.nearest_name}</div>
            <div style="font-size: 11px; color: #6E645E; margin-top: 2px;">~${Math.round(sc.nearest_minutes || 8)} min walk (${sc.distance_m ? `${Math.round(sc.distance_m)}m` : 'Nearby'})</div>
          </div>
        `);
        layerGroup.addLayer(schoolMarker);
        routeBounds.extend([sLat, sLon]);
      }

      // Hospital (Rose Red)
      if (selectedListing.hospital_access?.nearest_name) {
        const hs = selectedListing.hospital_access;
        const hLat = baseLat - 0.0032;
        const hLon = baseLon + 0.0035;
        const hospIcon = L.divIcon({
          className: 'facility-icon-hospital',
          html: `
            <div style="
              width: 28px;
              height: 28px;
              background: #E11D48;
              border: 2px solid #FFFFFF;
              border-radius: 50%;
              box-shadow: 0 3px 8px rgba(225, 29, 72, 0.4);
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 13px;
              color: white;
            ">
              🏥
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        const hospMarker = L.marker([hLat, hLon], { icon: hospIcon, zIndexOffset: 300 });
        hospMarker.bindPopup(`
          <div style="font-family: inherit; min-width: 160px;">
            <span style="font-size: 10px; font-weight: 700; color: #E11D48; text-transform: uppercase;">Hospital (Chennai Health OGD)</span>
            <div style="font-size: 12px; font-weight: 700; color: #2C2523; margin-top: 2px;">${hs.nearest_name}</div>
            <div style="font-size: 11px; color: #6E645E; margin-top: 2px;">~${Math.round(hs.nearest_minutes || 12)} min (${hs.distance_m ? `${Math.round(hs.distance_m)}m` : 'Nearby'})</div>
          </div>
        `);
        layerGroup.addLayer(hospMarker);
        routeBounds.extend([hLat, hLon]);
      }

      // Pharmacy (Amber)
      if (selectedListing.pharmacy_access?.nearest_name) {
        const ph = selectedListing.pharmacy_access;
        const pLat = baseLat + 0.0028;
        const pLon = baseLon + 0.0032;
        const pharmIcon = L.divIcon({
          className: 'facility-icon-pharmacy',
          html: `
            <div style="
              width: 28px;
              height: 28px;
              background: #D97706;
              border: 2px solid #FFFFFF;
              border-radius: 50%;
              box-shadow: 0 3px 8px rgba(217, 119, 6, 0.4);
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 13px;
              color: white;
            ">
              💊
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        const pharmMarker = L.marker([pLat, pLon], { icon: pharmIcon, zIndexOffset: 300 });
        pharmMarker.bindPopup(`
          <div style="font-family: inherit; min-width: 160px;">
            <span style="font-size: 10px; font-weight: 700; color: #D97706; text-transform: uppercase;">Pharmacy (OSM)</span>
            <div style="font-size: 12px; font-weight: 700; color: #2C2523; margin-top: 2px;">${ph.nearest_name}</div>
            <div style="font-size: 11px; color: #6E645E; margin-top: 2px;">~${Math.round(ph.nearest_minutes || 5)} min walk (${ph.distance_m ? `${Math.round(ph.distance_m)}m` : 'Nearby'})</div>
          </div>
        `);
        layerGroup.addLayer(pharmMarker);
        routeBounds.extend([pLat, pLon]);
      }
    }

    // Camera adjustment: fit route bounds if home is selected, otherwise fit all listings
    if (routeBounds) {
      map.fitBounds(routeBounds, { padding: [50, 50], maxZoom: 15 });
    } else if (listings.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    } else {
      map.setView([workplace.lat, workplace.lon], 12);
    }
  }, [workplace, searchRadiusKm, listings, selectedListingId, onSelectListing]);

  return (
    <div className="relative w-full h-full min-h-[380px] lg:min-h-[500px] rounded-2xl overflow-hidden border border-[#E2E8F0] shadow-sm bg-[#F7F9FC]">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating map badge / legend */}
      <div className="absolute top-3 left-3 z-[1000] bg-white/95 backdrop-blur-sm px-3.5 py-2.5 rounded-xl border border-[#E2E8F0] shadow-sm text-xs space-y-1.5 pointer-events-auto">
        <div className="flex items-center space-x-2 text-[#102033]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#0B1F3A]" />
          <span className="font-bold">Workplace ({workplace.label})</span>
        </div>
        <div className="flex items-center space-x-2 text-[#607080]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#1261D6]" />
          <span className="font-semibold text-[#102033]">Rental Homes ({listings.length})</span>
        </div>

        {selectedListingId && (
          <div className="pt-1.5 mt-1 border-t border-[#E2E8F0] space-y-1 text-[11px]">
            <div className="flex items-center space-x-1.5 text-[#1261D6] font-bold">
              <span className="w-3.5 h-0.5 bg-[#1261D6] rounded-full inline-block" />
              <span>Door-to-door transit route</span>
            </div>
            <div className="flex items-center space-x-3 text-[#607080]">
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-[#10B981]" />
                <span>School</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-[#EF4444]" />
                <span>Hospital</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-[#8B5CF6]" />
                <span>Pharmacy</span>
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
