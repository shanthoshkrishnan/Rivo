import React, { useEffect, useRef, useState } from 'react';
import { setOptions, importLibrary } from '@googlemaps/js-api-loader';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RecommendationResult } from '../../types/api';
import {
  Train,
  Bike,
  Car,
  Navigation,
  Clock,
  ShieldCheck,
  School,
  HeartPulse,
  Pill,
  Layers,
  Bus,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { fetchFacilityLayers, FacilityLayersResponse, MapFacility } from '../../services/api';

export type TravelModeKey = 'TRANSIT' | 'TWO_WHEELER' | 'DRIVE' | 'WALK';

interface RivoGoogleMapProps {
  workplace: { lat: number; lon: number; label: string };
  searchRadiusKm: number;
  listings: RecommendationResult[];
  selectedListingId: string | null;
  hoveredListingId?: string | null;
  selectedTravelMode: TravelModeKey;
  onSelectTravelMode: (mode: TravelModeKey) => void;
  onSelectListing: (listing: RecommendationResult) => void;
}

export const RivoGoogleMap: React.FC<RivoGoogleMapProps> = ({
  workplace,
  searchRadiusKm,
  listings,
  selectedListingId,
  hoveredListingId,
  selectedTravelMode,
  onSelectTravelMode,
  onSelectListing,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [useLeaflet, setUseLeaflet] = useState<boolean>(true);
  const [mapEngine, setMapEngine] = useState<'google' | 'leaflet'>('leaflet');
  const [mapError, setMapError] = useState<string | null>(null);

  // Facility Layers Control State
  const [showLayerMenu, setShowLayerMenu] = useState<boolean>(false);
  const [showHomes, setShowHomes] = useState<boolean>(true);
  const [showWorkplace, setShowWorkplace] = useState<boolean>(true);
  const [showTransit, setShowTransit] = useState<boolean>(true);
  const [showSchools, setShowSchools] = useState<boolean>(true);
  const [showHospitals, setShowHospitals] = useState<boolean>(true);
  const [showPharmacies, setShowPharmacies] = useState<boolean>(true);
  const [showJobs, setShowJobs] = useState<boolean>(false);

  // Nearby Essentials Drawer State
  const [showEssentialsDrawer, setShowEssentialsDrawer] = useState<boolean>(true);

  // Fetched facility data
  const [facilitiesData, setFacilitiesData] = useState<FacilityLayersResponse>({
    schools: [],
    hospitals: [],
    pharmacies: [],
    transit: [],
    workplaces: [],
  });

  // References for Google Maps
  const gMapInstanceRef = useRef<google.maps.Map | null>(null);
  const gMarkersRef = useRef<Map<string, google.maps.Marker>>(new Map());
  const gFacilityMarkersRef = useRef<google.maps.Marker[]>([]);
  const gPolylineRef = useRef<google.maps.Polyline | null>(null);
  const gCircleRef = useRef<google.maps.Circle | null>(null);

  // References for Leaflet Map
  const lMapInstanceRef = useRef<L.Map | null>(null);
  const lLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const lFacilitiesLayerGroupRef = useRef<L.LayerGroup | null>(null);

  const selectedListing = listings.find((l) => l.listing_id === selectedListingId);

  // Active route for selected travel mode
  const activeRoute = selectedListing
    ? selectedListing.all_routes?.find((r) => r.mode === selectedTravelMode) || selectedListing.best_route
    : null;

  const activeDurationMin = activeRoute
    ? activeRoute.duration_minutes ?? activeRoute.duration_min ?? Math.round((activeRoute.duration_seconds || 0) / 60)
    : null;

  const distanceKm = activeRoute?.distance_km ?? (activeRoute?.distance_m ? +(activeRoute.distance_m / 1000).toFixed(1) : undefined);

  // Monthly travel cost calculation
  let activeMonthlyCost = activeRoute?.monthly_commute_cost;
  if (activeMonthlyCost === undefined) {
    if (selectedTravelMode === 'TRANSIT') {
      const fare = activeRoute?.fare_amount ?? activeRoute?.fare_inr ?? 25;
      activeMonthlyCost = Math.round(fare * 2 * 22);
    } else if (selectedTravelMode === 'TWO_WHEELER') {
      const dist = distanceKm ?? 12;
      activeMonthlyCost = Math.round(((dist * 2 * 22) / 45) * 105);
    } else if (selectedTravelMode === 'DRIVE') {
      const dist = distanceKm ?? 12;
      activeMonthlyCost = Math.round(((dist * 2 * 22) / 14) * 105);
    } else {
      activeMonthlyCost = 0;
    }
  }

  // Load facilities layers around workplace or selected property
  useEffect(() => {
    const centerLat = selectedListing?.latitude ?? workplace.lat;
    const centerLon = selectedListing?.longitude ?? workplace.lon;
    fetchFacilityLayers({ lat: centerLat, lon: centerLon, radius_km: 15 }).then((data) => {
      setFacilitiesData(data);
    });
  }, [workplace.lat, workplace.lon, selectedListing?.latitude, selectedListing?.longitude]);

  // 1. Listen for Google Maps auth failures
  useEffect(() => {
    (window as any).gm_authFailure = () => {
      console.warn('[MAP] Google Maps auth failure. Fallback to Carto/OSM engine.');
      setUseLeaflet(true);
      setMapEngine('leaflet');
      setMapError('Google Maps key unauthorized or unbilled. Carto/OSM vector engine active.');
    };
  }, []);

  // 2. Initialize Leaflet Map
  useEffect(() => {
    if (!useLeaflet || !mapContainerRef.current) return;

    if (lMapInstanceRef.current) {
      lMapInstanceRef.current.remove();
      lMapInstanceRef.current = null;
    }
    mapContainerRef.current.innerHTML = '';

    const map = L.map(mapContainerRef.current, {
      center: [workplace.lat, workplace.lon],
      zoom: 12,
      zoomControl: false,
    });

    const cartoKey = import.meta.env.VITE_CARTO_API_KEY || 'cb1_3ztt_1_a14e158425019703bd7c6888';
    const tileUrl = `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${cartoKey}`;

    L.tileLayer(tileUrl, {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const facilitiesGroup = L.layerGroup().addTo(map);
    const mainGroup = L.layerGroup().addTo(map);

    lMapInstanceRef.current = map;
    lFacilitiesLayerGroupRef.current = facilitiesGroup;
    lLayerGroupRef.current = mainGroup;

    return () => {
      if (lMapInstanceRef.current) {
        lMapInstanceRef.current.remove();
        lMapInstanceRef.current = null;
      }
    };
  }, [useLeaflet, workplace.lat, workplace.lon]);

  // 3. Render Leaflet Facilities Layers
  useEffect(() => {
    if (!useLeaflet) return;
    const facGroup = lFacilitiesLayerGroupRef.current;
    if (!facGroup) return;

    facGroup.clearLayers();

    const addFacilityMarker = (fac: MapFacility, iconEmoji: string, bg: string) => {
      const icon = L.divIcon({
        className: 'custom-facility-marker',
        html: `
          <div style="
            background: ${bg};
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            cursor: pointer;
          " title="${fac.name}">
            ${iconEmoji}
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const m = L.marker([fac.latitude, fac.longitude], { icon, zIndexOffset: 50 });
      m.bindPopup(`
        <div style="min-width: 170px; font-family: inherit;">
          <div style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #0878D1; margin-bottom: 2px;">
            ${fac.verification_state} · ${fac.category}
          </div>
          <div style="font-size: 12px; font-weight: 800; color: #06243A; margin-bottom: 4px;">
            ${fac.name}
          </div>
          ${fac.address ? `<div style="font-size: 11px; color: #607080;">${fac.address}</div>` : ''}
          ${fac.distance_km ? `<div style="font-size: 11px; font-weight: 700; color: #0878D1; margin-top: 4px;">${fac.distance_km} km away</div>` : ''}
        </div>
      `);
      facGroup.addLayer(m);
    };

    if (showSchools) {
      facilitiesData.schools.forEach((f) => addFacilityMarker(f, '🏫', '#0878D1'));
    }
    if (showHospitals) {
      facilitiesData.hospitals.forEach((f) => addFacilityMarker(f, '🏥', '#EF4444'));
    }
    if (showPharmacies) {
      facilitiesData.pharmacies.forEach((f) => addFacilityMarker(f, '💊', '#10B981'));
    }
    if (showTransit) {
      facilitiesData.transit.forEach((f) => addFacilityMarker(f, f.type === 'metro_station' ? '🚇' : '🚌', '#06243A'));
    }
    if (showJobs) {
      facilitiesData.workplaces.forEach((f) => addFacilityMarker(f, '💼', '#6B21A8'));
    }
  }, [useLeaflet, facilitiesData, showSchools, showHospitals, showPharmacies, showTransit, showJobs]);

  // 4. Update Leaflet Map Markers & Route
  useEffect(() => {
    if (!useLeaflet) return;
    const map = lMapInstanceRef.current;
    const layerGroup = lLayerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // 1. Search radius circle
    const circle = L.circle([workplace.lat, workplace.lon], {
      radius: searchRadiusKm * 1000,
      color: '#0878D1',
      weight: 1.5,
      opacity: 0.35,
      fillColor: '#F3F8FC',
      fillOpacity: 0.12,
      dashArray: '4, 4',
    });
    layerGroup.addLayer(circle);

    // 2. Workplace Marker
    if (showWorkplace) {
      const workplaceIcon = L.divIcon({
        className: 'custom-workplace-icon',
        html: `
          <div style="
            width: 34px;
            height: 34px;
            background: #06243A;
            border: 2.5px solid #F5C542;
            border-radius: 50%;
            box-shadow: 0 4px 14px rgba(6, 36, 58, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
          ">
            📍
          </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });

      const workplaceMarker = L.marker([workplace.lat, workplace.lon], { icon: workplaceIcon, zIndexOffset: 1000 });
      workplaceMarker.bindPopup(`
        <div style="font-family: inherit; min-width: 150px; color: #06243A;">
          <span style="font-size: 10px; text-transform: uppercase; font-weight: 800; color: #0878D1;">WORKPLACE ANCHOR</span>
          <h4 style="margin: 2px 0 0 0; font-size: 13px; font-weight: 800;">${workplace.label}</h4>
        </div>
      `);
      layerGroup.addLayer(workplaceMarker);
    }

    // 3. Rental Listing Markers
    if (showHomes) {
      listings.forEach((item) => {
        if (item.latitude == null || item.longitude == null) return;
        const isSelected = item.listing_id === selectedListingId;
        const isHovered = item.listing_id === hoveredListingId;
        const rentFmt = item.rent_monthly ? `₹${(item.rent_monthly / 1000).toFixed(0)}k` : '₹--';

        const listingIcon = L.divIcon({
          className: 'custom-listing-icon',
          html: `
            <div style="
              background: ${isSelected ? '#0878D1' : '#FFFFFF'};
              color: ${isSelected ? '#FFFFFF' : '#06243A'};
              border: ${isSelected ? '2.5px solid #FFFFFF' : '1.5px solid #CBD5E1'};
              outline: ${isSelected ? '3px solid #F5C542' : isHovered ? '2px solid #0878D1' : 'none'};
              padding: 3px 8px;
              border-radius: 9999px;
              font-size: 11px;
              font-weight: 800;
              display: inline-flex;
              align-items: center;
              gap: 4px;
              box-shadow: 0 4px 12px rgba(8, 120, 209, ${isSelected ? '0.45' : '0.15'});
              white-space: nowrap;
              transform: ${isSelected ? 'scale(1.18)' : isHovered ? 'scale(1.08)' : 'scale(1)'};
              transition: all 0.15s ease;
            ">
              <span>${rentFmt}</span>
            </div>
          `,
          iconSize: [56, 26],
          iconAnchor: [28, 13],
        });

        const marker = L.marker([item.latitude, item.longitude], {
          icon: listingIcon,
          zIndexOffset: isSelected ? 600 : isHovered ? 450 : 150,
        });

        marker.on('click', () => {
          onSelectListing(item);
        });

        marker.bindPopup(`
          <div style="min-width: 190px; font-family: inherit; padding: 2px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
              <span style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #607080;">${item.locality || 'Chennai'}</span>
              <span style="font-size: 14px; font-weight: 800; color: #0878D1;">₹${(item.rent_monthly || 0).toLocaleString()}</span>
            </div>
            <div style="font-size: 12px; color: #06243A; margin-bottom: 4px;">
              ${item.bhk ? `${item.bhk} BHK • ` : ''}${item.area_sqft ? `${item.area_sqft} sq ft` : 'Residential'}
            </div>
            <div style="font-size: 10px; color: #607080;">
              ${item.address || 'DEMO PROPERTY — Verified Coordinates'}
            </div>
          </div>
        `);

        layerGroup.addLayer(marker);
      });
    }

    // 4. Draw Route Polyline from Exact Property to Workplace
    if (selectedListing && selectedListing.latitude != null && selectedListing.longitude != null) {
      const routeToDraw =
        selectedListing.all_routes?.find((r) => r.mode === selectedTravelMode) ||
        selectedListing.best_route;

      const polylineCoords: L.LatLngTuple[] = [];

      if (routeToDraw?.route_geometry) {
        try {
          const geo = JSON.parse(routeToDraw.route_geometry);
          if (geo.type === 'LineString' && Array.isArray(geo.coordinates)) {
            geo.coordinates.forEach((coord: [number, number]) => {
              if (Array.isArray(coord) && coord.length >= 2) {
                polylineCoords.push([coord[1], coord[0]]);
              }
            });
          }
        } catch {
          // fallback
        }
      }

      // Always anchor directly to property and workplace
      if (polylineCoords.length === 0) {
        polylineCoords.push([selectedListing.latitude, selectedListing.longitude]);
        polylineCoords.push([workplace.lat, workplace.lon]);
      } else {
        // Ensure ends connect exactly
        polylineCoords[0] = [selectedListing.latitude, selectedListing.longitude];
        polylineCoords[polylineCoords.length - 1] = [workplace.lat, workplace.lon];
      }

      let routeColor = '#0878D1';
      if (selectedTravelMode === 'TWO_WHEELER') routeColor = '#E69900';
      if (selectedTravelMode === 'DRIVE') routeColor = '#06243A';
      if (selectedTravelMode === 'WALK') routeColor = '#10B981';

      const polyline = L.polyline(polylineCoords, {
        color: routeColor,
        weight: 5,
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round',
      });
      layerGroup.addLayer(polyline);

      const bounds = L.latLngBounds([
        [workplace.lat, workplace.lon],
        [selectedListing.latitude, selectedListing.longitude],
      ]);
      map.fitBounds(bounds, { padding: [60, 60] });
    }
  }, [
    useLeaflet,
    workplace,
    searchRadiusKm,
    listings,
    selectedListingId,
    selectedTravelMode,
    hoveredListingId,
    showHomes,
    showWorkplace,
  ]);

  const nf = selectedListing?.nearest_facilities || {};

  return (
    <div className="relative w-full h-full bg-[#F3F8FC] overflow-hidden flex flex-col">
      {/* Top Travel Mode & Summary Toolbar */}
      <div className="bg-white border-b border-[#E2E8F0] p-3 px-4 flex flex-wrap items-center justify-between gap-3 z-10 shadow-xs">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-extrabold text-[#06243A] uppercase tracking-wider">
            Travel By:
          </span>
          <div className="inline-flex rounded-xl bg-[#F3F8FC] p-1 border border-[#E2E8F0]">
            {(
              [
                { mode: 'TRANSIT', label: 'Transit', icon: Train },
                { mode: 'TWO_WHEELER', label: '2-Wheeler', icon: Bike },
                { mode: 'DRIVE', label: 'Car', icon: Car },
                { mode: 'WALK', label: 'Walk', icon: Navigation },
              ] as const
            ).map(({ mode, label, icon: Icon }) => (
              <button
                key={mode}
                type="button"
                onClick={() => onSelectTravelMode(mode)}
                className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  selectedTravelMode === mode
                    ? 'bg-[#0878D1] text-white shadow-xs'
                    : 'text-[#607080] hover:text-[#06243A]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Selected Home Commute Metrics & Layer Toggle */}
        <div className="flex items-center space-x-3 text-xs">
          {selectedListing && activeDurationMin && (
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-1 font-extrabold text-[#06243A]">
                <Clock className="w-3.5 h-3.5 text-[#0878D1]" />
                <span>{activeDurationMin} min</span>
              </div>
              {distanceKm !== undefined && (
                <span className="text-[#607080]">· {distanceKm} km</span>
              )}
              <div className="font-extrabold text-[#0878D1] bg-[#F3F8FC] px-2.5 py-0.5 rounded-lg border border-[#BFDBFE]">
                {selectedTravelMode === 'WALK' ? '₹0 fare' : `₹${activeMonthlyCost.toLocaleString()}/mo`}
              </div>
            </div>
          )}

          {/* Layer Control Dropdown Button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowLayerMenu(!showLayerMenu)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#F8FAFC] hover:bg-[#EEF5FF] text-[#06243A] border border-[#CBD5E1] font-bold text-xs shadow-2xs transition-colors cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5 text-[#0878D1]" />
              <span>Layers</span>
              <ChevronDown className="w-3 h-3 text-[#607080]" />
            </button>

            {showLayerMenu && (
              <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-xl border border-[#CBD5E1] p-3 z-30 space-y-2 text-xs">
                <div className="font-extrabold text-[#06243A] uppercase tracking-wider text-[10px] pb-1 border-b border-[#E2E8F0]">
                  Map Facility Layers
                </div>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showHomes}
                    onChange={(e) => setShowHomes(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>🏠 Homes</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showWorkplace}
                    onChange={(e) => setShowWorkplace(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>📍 Workplace</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showTransit}
                    onChange={(e) => setShowTransit(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>🚇 Transit (Metro/Bus)</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showSchools}
                    onChange={(e) => setShowSchools(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>🏫 Schools</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showHospitals}
                    onChange={(e) => setShowHospitals(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>🏥 Hospitals</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showPharmacies}
                    onChange={(e) => setShowPharmacies(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>💊 Pharmacies</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showJobs}
                    onChange={(e) => setShowJobs(e.target.checked)}
                    className="rounded text-[#0878D1]"
                  />
                  <span>💼 Employment Hubs</span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Map Canvas */}
      <div className="relative flex-1 w-full h-full">
        {mapError && (
          <div className="absolute top-2 right-2 left-2 z-20 bg-amber-50 border border-amber-200 text-amber-900 px-3 py-1.5 rounded-lg text-xs flex items-center justify-between shadow-xs">
            <div className="flex items-center space-x-1.5">
              <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />
              <span>{mapError}</span>
            </div>
            <button
              type="button"
              onClick={() => setMapError(null)}
              className="text-amber-700 hover:text-amber-900 font-bold ml-2 text-sm leading-none"
            >
              ×
            </button>
          </div>
        )}

        <div ref={mapContainerRef} className="w-full h-full" />

        {/* Top-Left Provenance & Legend Overlay */}
        <div className="absolute top-3 left-3 bg-white/95 backdrop-blur-md rounded-xl p-2.5 px-3 border border-[#E2E8F0] shadow-sm z-10 space-y-1.5 text-[11px] text-[#06243A]">
          <div className="font-extrabold text-[10px] text-[#0878D1] uppercase tracking-wider">
            {activeRoute?.source_label || 'RIVO / GTFS Multi-Modal Network'}
          </div>
          <div className="flex items-center space-x-3 text-[10px]">
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[#06243A] ring-2 ring-[#F5C542]" />
              <span>Workplace</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0878D1] ring-2 ring-[#F5C542]" />
              <span>Selected Home</span>
            </span>
          </div>
        </div>

        {/* Bottom "Nearby Essentials" Drawer (Requirement 20) */}
        {selectedListing && (
          <div className="absolute bottom-3 right-3 max-w-xs w-full bg-white/95 backdrop-blur-md rounded-2xl border border-[#E2E8F0] shadow-xl p-3 z-10 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-extrabold text-[#06243A] uppercase tracking-wider">
                Nearby Essentials ({selectedListing.locality})
              </span>
              <button
                type="button"
                onClick={() => setShowEssentialsDrawer(!showEssentialsDrawer)}
                className="text-[#607080] hover:text-[#06243A] cursor-pointer"
              >
                {showEssentialsDrawer ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
              </button>
            </div>

            {showEssentialsDrawer && (
              <div className="space-y-1.5 text-xs text-[#06243A] pt-1 border-t border-[#E2E8F0]/80">
                <div className="flex items-center justify-between">
                  <span className="flex items-center space-x-1.5">
                    <School className="w-3.5 h-3.5 text-[#0878D1]" />
                    <span className="truncate max-w-[140px]">{nf.school?.name || 'Local School'}</span>
                  </span>
                  <b className="text-[#0878D1]">
                    {nf.school?.distance_m ? `${(nf.school.distance_m / 1000).toFixed(1)} km` : '—'}
                  </b>
                </div>

                <div className="flex items-center justify-between">
                  <span className="flex items-center space-x-1.5">
                    <HeartPulse className="w-3.5 h-3.5 text-[#EF4444]" />
                    <span className="truncate max-w-[140px]">{nf.hospital?.name || 'Hospital'}</span>
                  </span>
                  <b className="text-[#EF4444]">
                    {nf.hospital?.distance_m ? `${(nf.hospital.distance_m / 1000).toFixed(1)} km` : '—'}
                  </b>
                </div>

                <div className="flex items-center justify-between">
                  <span className="flex items-center space-x-1.5">
                    <Pill className="w-3.5 h-3.5 text-[#10B981]" />
                    <span className="truncate max-w-[140px]">{nf.pharmacy?.name || 'Pharmacy'}</span>
                  </span>
                  <b className="text-[#10B981]">
                    {nf.pharmacy?.distance_m ? `${(nf.pharmacy.distance_m / 1000).toFixed(1)} km` : '—'}
                  </b>
                </div>

                <div className="flex items-center justify-between">
                  <span className="flex items-center space-x-1.5">
                    <Bus className="w-3.5 h-3.5 text-[#E69900]" />
                    <span className="truncate max-w-[140px]">{nf.bus_stop?.name || 'Bus Stop'}</span>
                  </span>
                  <b className="text-[#E69900]">
                    {nf.bus_stop?.distance_m ? `${Math.round(nf.bus_stop.distance_m)} m` : '—'}
                  </b>
                </div>

                <div className="flex items-center justify-between">
                  <span className="flex items-center space-x-1.5">
                    <Train className="w-3.5 h-3.5 text-[#06243A]" />
                    <span className="truncate max-w-[140px]">{nf.metro?.name || 'Metro Station'}</span>
                  </span>
                  <b className="text-[#06243A]">
                    {nf.metro?.distance_m ? `${(nf.metro.distance_m / 1000).toFixed(1)} km` : '—'}
                  </b>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
