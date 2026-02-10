import { useEffect } from 'react';
import { useMap } from 'react-map-gl';

export function MapboxHeatmap({ points }) {
  const { current: map } = useMap();
  const hasValidPoints = Array.isArray(points) && points.length > 0;

  useEffect(() => {
    if (!map) return;

    const layerId = 'heatmap-layer';
    const sourceId = 'heatmap-source';

    const handleLoad = () => {
      try {
        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }

        if (!hasValidPoints) {
          return;
        }

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

        map.addSource(sourceId, {
          type: 'geojson',
          data: geojson
        });

        map.addLayer({
          id: layerId,
          type: 'heatmap',
          source: sourceId,
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
        });
      } catch (error) {
        console.error('Error adding heatmap:', error);
      }
    };

    const isLoaded = Boolean(map.loaded && map.loaded());
    if (isLoaded) {
      handleLoad();
    } else if (map.on) {
      map.on('load', handleLoad);
    }

    return () => {
      try {
        if (!isLoaded && map.off) {
          map.off('load', handleLoad);
        }
        if (map.getLayer && map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
        if (map.getSource && map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
      } catch (e) {
        // Map might be destroyed, ignore cleanup errors
      }
    };
  }, [map, points, hasValidPoints]);

  return null;
}
