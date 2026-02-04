import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import 'leaflet.heat'
import L from 'leaflet'

export function HeatmapLayer({ points }) {
    const map = useMap();
    useEffect(() => {
        if (!points || !Array.isArray(points) || points.length === 0) return;
        const heatData = points.map(p => [p.lat, p.lng, p.intensity || 0.5]);
        const layer = L.heatLayer(heatData, { radius: 25, blur: 15 }).addTo(map);
        return () => { if (map.hasLayer(layer)) map.removeLayer(layer); };
    }, [map, points]);
    return null;
}
