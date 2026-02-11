import { Source, Layer } from './InteractiveMap';

export function MapboxHeatmap({ points }) {
  if (!points || !Array.isArray(points) || points.length === 0) return null;

  const geojson = {
    type: 'FeatureCollection',
    features: points.map(p => ({
      type: 'Feature',
      properties: {
        intensity: p.intensity || 0.5
      },
      geometry: {
        type: 'Point',
        coordinates: [p.lng, p.lat]
      }
    }))
  };

  const heatmapLayer = {
    id: 'heatmap-layer',
    type: 'heatmap',
    paint: {
      'heatmap-weight': [
        'interpolate',
        ['linear'],
        ['get', 'intensity'],
        0, 0,
        1, 1
      ],
      'heatmap-intensity': [
        'interpolate',
        ['linear'],
        ['zoom'],
        0, 1,
        15, 3
      ],
      'heatmap-color': [
        'interpolate',
        ['linear'],
        ['heatmap-density'],
        0, 'rgba(33,102,172,0)',
        0.2, 'rgb(103,169,207)',
        0.4, 'rgb(209,229,240)',
        0.6, 'rgb(253,219,199)',
        0.8, 'rgb(239,138,98)',
        1, 'rgb(178,24,43)'
      ],
      'heatmap-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        0, 2,
        15, 25
      ],
      'heatmap-opacity': [
        'interpolate',
        ['linear'],
        ['zoom'],
        7, 1,
        15, 0.8
      ]
    }
  };

  return (
    <Source type="geojson" data={geojson}>
      <Layer {...heatmapLayer} />
    </Source>
  );
}
