import { useEffect } from 'react';
import { useMap } from 'react-map-gl';

export function MapboxHeatmap({ points }) {
  const { current: map } = useMap();

  useEffect(() => {
    if (!map || !points || !Array.isArray(points) || points.length === 0) return;

    const layerId = 'heatmap-layer';
    const sourceId = 'heatmap-source';

    // Wait for map to load
    const handleLoad = () => {
      try {
        // Remove existing layer and source if present
        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }

        // Create GeoJSON from points
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

        // Add source
        map.addSource(sourceId, {
          type: 'geojson',
          data: geojson
        });

      // Add heatmap layer
      map.addLayer({
        id: layerId,
        type: 'heatmap',
        source: sourceId,
        paint: {
          // Increase the heatmap weight based on intensity property
          'heatmap-weight': [
            'interpolate',
            ['linear'],
            ['get', 'intensity'],
            0, 0,
            1, 1
          ],
          // Increase the heatmap color weight by zoom level
          'heatmap-intensity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            0, 1,
            15, 3
          ],
          // Color ramp for heatmap
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
          // Adjust the heatmap radius by zoom level
          'heatmap-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            0, 2,
            15, 25
          ],
          // Transition from heatmap to circle layer by zoom level
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

    if (map.loaded && map.loaded()) {
      handleLoad();
    } else if (map.on) {
      map.on('load', handleLoad);
    }

    return () => {
      try {
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
  }, [map, points]);

  return null;
}
