import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Layers, Info, X } from 'lucide-react';
import { ScenarioMapData } from '../../types/api';

interface CityMapProps {
  mapData: ScenarioMapData | undefined;
  scenarioType: 'transit' | 'housing';
  selectedCorridorName?: string;
  selectedHousingName?: string;
  currentWorkers?: number;
  proposedWorkers?: number;
  gainWorkers?: number;
}

export const CityMap: React.FC<CityMapProps> = ({
  mapData,
  scenarioType,
  selectedCorridorName,
  selectedHousingName,
  currentWorkers = 2150,
  proposedWorkers = 2660,
  gainWorkers = 510,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  const [mapMode, setMapMode] = useState<'current' | 'proposed' | 'compare'>('compare');
  const [activeFeature, setActiveFeature] = useState<{
    title: string;
    subtitle: string;
    tag: string;
    details: Array<{ label: string; value: string }>;
    simulationNote?: string;
  } | null>(null);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Center on Chennai CMA (Porur / Central axis)
    const map = L.map(mapContainerRef.current, {
      center: [13.045, 80.200],
      zoom: 11.5,
      zoomControl: false,
    });

    // Carto Voyager basemap with authorized API key (clean, watermark-free high legibility)
    const cartoKey = import.meta.env.VITE_CARTO_API_KEY || 'cb1_3ztt_1_a14e158425019703bd7c6888';
    const tileUrl = `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${cartoKey}`;

    L.tileLayer(tileUrl, {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 18,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Render Spatial Layers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup || !mapData) return;

    layerGroup.clearLayers();

    // 1. Current Reachable Area (Blue)
    if (mapMode === 'current' || mapMode === 'compare') {
      if (mapData.current_reachable_area && mapData.current_reachable_area.length > 0) {
        const currentPolygon = L.polygon(mapData.current_reachable_area, {
          color: '#1261D6',
          weight: 2,
          opacity: 0.85,
          fillColor: '#1261D6',
          fillOpacity: mapMode === 'compare' ? 0.12 : 0.22,
          dashArray: mapMode === 'compare' ? '5, 5' : undefined,
        });

        currentPolygon.on('click', () => {
          setActiveFeature({
            title: 'Current Baseline Reach (45 min)',
            subtitle: 'Door-to-door transit catchment before intervention',
            tag: 'Baseline Network',
            details: [
              { label: 'Reachable Workers', value: currentWorkers.toLocaleString() },
              { label: 'Commute Baseline', value: '42.0 min median' },
              { label: 'Network', value: 'MTC Bus + Suburban Rail' },
            ],
          });
        });

        layerGroup.addLayer(currentPolygon);
      }
    }

    // 2. Proposed Reachable Area (Cyan)
    if (mapMode === 'proposed' || mapMode === 'compare') {
      if (mapData.proposed_reachable_area && mapData.proposed_reachable_area.length > 0) {
        const proposedPolygon = L.polygon(mapData.proposed_reachable_area, {
          color: '#06B6D4',
          weight: 2.5,
          opacity: 0.95,
          fillColor: '#06B6D4',
          fillOpacity: 0.20,
        });

        proposedPolygon.on('click', () => {
          setActiveFeature({
            title: 'Projected Reach (45 min)',
            subtitle: 'Expanded accessibility envelope with intervention',
            tag: 'Simulation Result',
            details: [
              { label: 'Projected Reach', value: `${proposedWorkers.toLocaleString()} workers` },
              { label: 'Worker Gain', value: `+${gainWorkers.toLocaleString()} workers` },
              { label: 'Access Shift', value: 'Western & Central corridors unlocked' },
            ],
            simulationNote: 'Scenario simulation — not current service',
          });
        });

        layerGroup.addLayer(proposedPolygon);
      }
    }

    // 3. 800m Station Pedestrian Catchments (Yellow translucent buffers)
    if (mapData.catchment_circles && (mapMode === 'proposed' || mapMode === 'compare')) {
      mapData.catchment_circles.forEach((circle) => {
        const c = L.circle([circle.lat, circle.lon], {
          radius: circle.radius_meters || 800,
          color: '#F59E0B',
          weight: 1.2,
          opacity: 0.7,
          fillColor: '#F7C948',
          fillOpacity: 0.18,
          dashArray: '3, 4',
        });

        c.on('click', () => {
          setActiveFeature({
            title: `${circle.name} — 800m Catchment`,
            subtitle: 'Pedestrian first/last-mile transit access zone',
            tag: '800m Station Buffer',
            details: [
              { label: 'Standard Buffer', value: '800 meters pedestrian walk' },
              { label: 'Density Baseline', value: '16,500 pop / km² (GCC 2025)' },
              { label: 'Status', value: 'CMRL Phase II station catchment' },
            ],
            simulationNote: 'Scenario simulation — planned station buffer',
          });
        });

        layerGroup.addLayer(c);
      });
    }

    // 4. Corridors (Polylines)
    if (mapData.corridors) {
      mapData.corridors.forEach((corridor) => {
        const isSelected = corridor.is_selected;
        const polyline = L.polyline(corridor.coordinates, {
          color: isSelected ? '#D97706' : '#64748B',
          weight: isSelected ? 4.5 : 2.5,
          opacity: isSelected ? 0.95 : 0.5,
          dashArray: isSelected ? undefined : '4, 4',
        });

        polyline.on('click', () => {
          setActiveFeature({
            title: corridor.name,
            subtitle: `${corridor.length_km} km rapid transit alignment`,
            tag: isSelected ? 'Active Intervention' : 'Planned Corridor',
            details: [
              { label: 'Corridor Length', value: `${corridor.length_km} km` },
              { label: 'Target Completion', value: 'Late 2028 (CMRL Phase II)' },
              { label: 'Reachable Workers', value: `${currentWorkers} → ${proposedWorkers} (+${gainWorkers})` },
            ],
            simulationNote: 'Scenario simulation — not current operational service',
          });
        });

        layerGroup.addLayer(polyline);
      });
    }

    // 5. Stations (Markers)
    if (mapData.stations && (mapMode === 'proposed' || mapMode === 'compare')) {
      mapData.stations.forEach((st) => {
        const isTerminal = st.type === 'terminal' || st.type === 'major_interchange';
        const markerIcon = L.divIcon({
          className: 'city-station-icon',
          html: `
            <div style="
              width: ${isTerminal ? '20px' : '15px'};
              height: ${isTerminal ? '20px' : '15px'};
              background: #F7C948;
              border: 2px solid #0B1F3A;
              border-radius: 50%;
              box-shadow: 0 2px 6px rgba(11,31,58,0.35);
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 8px;
              font-weight: 800;
              color: #0B1F3A;
            ">
              ${isTerminal ? 'M' : ''}
            </div>
          `,
          iconSize: [isTerminal ? 20 : 15, isTerminal ? 20 : 15],
          iconAnchor: [isTerminal ? 10 : 7.5, isTerminal ? 10 : 7.5],
        });

        const m = L.marker([st.lat, st.lon], { icon: markerIcon });
        m.on('click', () => {
          setActiveFeature({
            title: st.name,
            subtitle: 'CMRL Phase II Proposed Station Node',
            tag: st.type?.replace('_', ' ').toUpperCase() || 'METRO STATION',
            details: [
              { label: 'Pedestrian Buffer', value: '800 meters' },
              { label: 'Corridor', value: selectedCorridorName || 'CMRL Phase II' },
              { label: 'Status', value: 'Under Construction (Target 2028)' },
            ],
            simulationNote: 'Scenario simulation — planned station',
          });
        });

        layerGroup.addLayer(m);
      });
    }

    // 6. Major Employment Clusters (Navy Badges)
    if (mapData.employment_clusters) {
      mapData.employment_clusters.forEach((cluster) => {
        const jobIcon = L.divIcon({
          className: 'city-job-icon',
          html: `
            <div style="
              padding: 3px 7px;
              background: #0B1F3A;
              border: 1.5px solid #FFFFFF;
              border-radius: 12px;
              color: #FFFFFF;
              font-size: 10px;
              font-weight: 700;
              box-shadow: 0 2px 8px rgba(11,31,58,0.3);
              display: flex;
              align-items: center;
              gap: 4px;
              white-space: nowrap;
            ">
              <span style="font-size: 11px;">🏢</span>
              <span>${cluster.name.split('/')[0].split('(')[0].trim()}</span>
            </div>
          `,
          iconAnchor: [40, 12],
        });

        const m = L.marker([cluster.lat, cluster.lon], { icon: jobIcon, zIndexOffset: 200 });
        m.on('click', () => {
          setActiveFeature({
            title: cluster.name,
            subtitle: cluster.category,
            tag: 'Employment Concentration',
            details: [
              { label: 'Estimated Jobs', value: `~${cluster.estimated_workers.toLocaleString()} workers` },
              { label: 'Category', value: cluster.category },
              { label: 'Catchment', value: 'Primary origin-destination target' },
            ],
          });
        });

        layerGroup.addLayer(m);
      });
    }

    // 7. Housing Sites
    if (mapData.housing_sites) {
      mapData.housing_sites.forEach((site) => {
        const isSelected = site.is_selected || scenarioType === 'housing';
        const houseIcon = L.divIcon({
          className: 'city-house-icon',
          html: `
            <div style="
              padding: 3px 8px;
              background: ${isSelected ? '#059669' : '#0B1F3A'};
              border: 2px solid ${isSelected ? '#A7F3D0' : '#FFFFFF'};
              border-radius: 12px;
              color: #FFFFFF;
              font-size: 10px;
              font-weight: 700;
              box-shadow: 0 2px 8px rgba(5,150,105,0.4);
              display: flex;
              align-items: center;
              gap: 4px;
              white-space: nowrap;
            ">
              <span>🏠</span>
              <span>${site.name.split(' ')[0]} Housing</span>
            </div>
          `,
          iconAnchor: [45, 12],
        });

        const m = L.marker([site.lat, site.lon], { icon: houseIcon, zIndexOffset: 300 });
        m.on('click', () => {
          setActiveFeature({
            title: site.name,
            subtitle: 'Workforce Housing Supply Site',
            tag: isSelected ? 'Active Housing Site' : 'Planned Housing Site',
            details: [
              { label: 'Planned Stock', value: `${site.units} units` },
              { label: 'Target Rent', value: `₹${site.target_rent.toLocaleString()} / month` },
              { label: 'Configuration', value: '1–2 BHK Workforce Units' },
            ],
            simulationNote: 'Scenario simulation — proposed workforce housing supply',
          });
        });

        layerGroup.addLayer(m);
      });
    }
  }, [mapData, mapMode, currentWorkers, proposedWorkers, gainWorkers, scenarioType, selectedCorridorName, selectedHousingName]);

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-[#CBD5E1] shadow-sm bg-white">
      {/* Top Map Controls Bar */}
      <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* Layer title tag */}
        <div className="pointer-events-auto bg-[#0B1F3A]/90 backdrop-blur-md text-white px-3 py-1.5 rounded-xl border border-white/10 shadow-md text-xs font-semibold flex items-center space-x-2">
          <Layers className="w-3.5 h-3.5 text-[#F7C948]" />
          <span>Interactive Spatial Canvas • Chennai CMA</span>
        </div>

        {/* View Mode Switcher: [ Current ] [ Proposed ] [ Compare ] */}
        <div className="pointer-events-auto bg-white/95 backdrop-blur-md rounded-xl p-1 shadow-md border border-[#CBD5E1] flex items-center space-x-1 text-xs">
          <button
            type="button"
            onClick={() => setMapMode('current')}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
              mapMode === 'current'
                ? 'bg-[#1261D6] text-white shadow-xs'
                : 'text-[#607080] hover:text-[#102033]'
            }`}
          >
            Current Access
          </button>
          <button
            type="button"
            onClick={() => setMapMode('proposed')}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
              mapMode === 'proposed'
                ? 'bg-[#06B6D4] text-white shadow-xs'
                : 'text-[#607080] hover:text-[#102033]'
            }`}
          >
            Proposed Access
          </button>
          <button
            type="button"
            onClick={() => setMapMode('compare')}
            className={`px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
              mapMode === 'compare'
                ? 'bg-[#0B1F3A] text-[#F7C948] shadow-xs'
                : 'text-[#607080] hover:text-[#102033]'
            }`}
          >
            Compare Both
          </button>
        </div>
      </div>

      {/* Map DOM Container */}
      <div ref={mapContainerRef} className="w-full h-[500px] z-0" />

      {/* Interactive Feature Info Flyout */}
      {activeFeature && (
        <div className="absolute bottom-14 left-4 z-[1000] w-80 bg-white/98 backdrop-blur-md rounded-xl p-4 border border-[#CBD5E1] shadow-xl space-y-2 animate-fadeIn">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#1261D6] bg-[#EEF5FF] px-2 py-0.5 rounded border border-[#CBD5E1]">
                {activeFeature.tag}
              </span>
              <h4 className="text-sm font-bold text-[#102033] mt-1">{activeFeature.title}</h4>
              <p className="text-[11px] text-[#607080]">{activeFeature.subtitle}</p>
            </div>
            <button
              type="button"
              onClick={() => setActiveFeature(null)}
              className="text-[#94A3B8] hover:text-[#102033] p-1 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="divide-y divide-[#F1F5F9] pt-1">
            {activeFeature.details.map((d, i) => (
              <div key={i} className="py-1 flex items-center justify-between text-xs">
                <span className="text-[#607080]">{d.label}</span>
                <span className="font-bold text-[#102033]">{d.value}</span>
              </div>
            ))}
          </div>

          {activeFeature.simulationNote && (
            <div className="pt-1.5 border-t border-[#F1F5F9] text-[10px] font-semibold text-[#D97706] flex items-center space-x-1">
              <Info className="w-3 h-3 text-[#D97706] shrink-0" />
              <span>{activeFeature.simulationNote}</span>
            </div>
          )}
        </div>
      )}

      {/* Map Legend Bar */}
      <div className="bg-[#F8FAFC] border-t border-[#E2E8F0] px-4 py-2.5 flex flex-wrap items-center justify-between text-xs text-[#607080] gap-3">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-1.5">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#1261D6]/20 border border-[#1261D6]" />
            <span className="text-[11px] font-medium text-[#102033]">Current 45m Reach</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#06B6D4]/30 border border-[#06B6D4]" />
            <span className="text-[11px] font-medium text-[#102033]">Proposed 45m Reach</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3.5 h-1.5 bg-[#F59E0B] rounded-full" />
            <span className="text-[11px] font-medium text-[#102033]">CMRL Corridor &amp; 800m Buffer</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#0B1F3A]" />
            <span className="text-[11px] font-medium text-[#102033]">Job Hubs</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#059669]" />
            <span className="text-[11px] font-medium text-[#102033]">Housing Stock</span>
          </div>
        </div>

        <div className="text-[10px] text-[#64748B] font-mono">
          Click any feature to inspect details • Projection: WGS84
        </div>
      </div>
    </div>
  );
};
