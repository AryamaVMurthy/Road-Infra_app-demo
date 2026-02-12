import { useState, useEffect } from 'react';
import { useMap } from 'react-map-gl';
import { Source, Layer } from './InteractiveMap';

export function MapboxHeatmap({ points }) {
  const { current: mapRef } = useMap();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!mapRef) return;

    const map = mapRef.getMap();
    if (!map) return;

    if (map.isStyleLoaded()) {
      setIsReady(true);
    } else {
      const handler = () => setIsReady(true);
      map.once('style.load', handler);
      return () => map.off('style.load', handler);
    }
  }, [mapRef]);

  const validPoints = Array.isArray(points)
    ? points.filter(
        (point) =>
          Number.isFinite(point?.lng) &&
          Number.isFinite(point?.lat) &&
          point.lng >= -180 &&
          point.lng <= 180 &&
          point.lat >= -90 &&
          point.lat <= 90
      )
    : [];

  if (!isReady || validPoints.length === 0) return null;

  const geojson = {
    type: 'FeatureCollection',
    features: validPoints.map((p) => ({
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
    <Source id="heatmap-source" type="geojson" data={geojson}>
      <Layer {...heatmapLayer} />
    </Source>
  );
}
