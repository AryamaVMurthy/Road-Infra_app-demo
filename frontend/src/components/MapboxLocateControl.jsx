import { useEffect } from 'react';
import { useMap } from 'react-map-gl';
import { Navigation } from 'lucide-react';
import { renderToString } from 'react-dom/server';
import mapboxgl from 'mapbox-gl';

export function MapboxLocateControl({ onFound }) {
  const { current: map } = useMap();

  useEffect(() => {
    if (!map) return;
    let marker = null;

    // Create control container
    const controlDiv = document.createElement('div');
    controlDiv.className = 'mapboxgl-ctrl mapboxgl-ctrl-group';
    controlDiv.style.margin = '10px';
    
    const button = document.createElement('button');
    button.className = 'mapboxgl-ctrl-icon';
    button.type = 'button';
    button.title = 'Get Current Location';
    button.style.backgroundImage = 'none';
    button.style.width = '29px';
    button.style.height = '29px';
    button.style.display = 'flex';
    button.style.alignItems = 'center';
    button.style.justifyContent = 'center';
    button.innerHTML = renderToString(<Navigation size={18} className="text-primary" />);
    
    button.onclick = () => {
      if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude, accuracy } = position.coords;
          const lngLat = [longitude, latitude];

          // Fly to location
          map.flyTo({
            center: lngLat,
            zoom: 18,
            essential: true
          });

          // Remove existing marker and circle
          if (marker) {
            marker.remove();
          }
          if (map.getLayer('location-circle')) {
            map.removeLayer('location-circle');
          }
          if (map.getSource('location-circle')) {
            map.removeSource('location-circle');
          }

          // Add marker
          marker = new mapboxgl.Marker()
            .setLngLat(lngLat)
            .setPopup(new mapboxgl.Popup().setHTML('<p>You are here</p>'))
            .addTo(map);
          
          marker.togglePopup();

          // Add accuracy circle
          const radiusInKm = accuracy / 1000;
          const points = 64;
          const coords = [];
          const distanceX = radiusInKm / (111.32 * Math.cos((latitude * Math.PI) / 180));
          const distanceY = radiusInKm / 110.574;

          for (let i = 0; i < points; i++) {
            const theta = (i / points) * (2 * Math.PI);
            const x = distanceX * Math.cos(theta);
            const y = distanceY * Math.sin(theta);
            coords.push([longitude + x, latitude + y]);
          }
          coords.push(coords[0]);

          map.addSource('location-circle', {
            type: 'geojson',
            data: {
              type: 'Feature',
              geometry: {
                type: 'Polygon',
                coordinates: [coords]
              }
            }
          });

          map.addLayer({
            id: 'location-circle',
            type: 'fill',
            source: 'location-circle',
            paint: {
              'fill-color': '#3B82F6',
              'fill-opacity': 0.2
            }
          });

          if (onFound) {
            onFound({ lat: latitude, lng: longitude });
          }
        },
        (error) => {
          console.error('Location error:', error.message);
          alert('Unable to retrieve your location');
        }
      );
    };

    controlDiv.appendChild(button);

    // Add control to map
    const topRightControls = map
      .getContainer()
      .querySelector('.mapboxgl-ctrl-top-right');
    if (topRightControls) {
      topRightControls.appendChild(controlDiv);
    }

    return () => {
      if (controlDiv && controlDiv.parentNode) {
        controlDiv.parentNode.removeChild(controlDiv);
      }
      if (marker) {
        marker.remove();
      }
      try {
        if (map && map.getLayer && map.getLayer('location-circle')) {
          map.removeLayer('location-circle');
        }
        if (map && map.getSource && map.getSource('location-circle')) {
          map.removeSource('location-circle');
        }
      } catch (e) {
        // Map might already be destroyed, ignore cleanup errors
      }
    };
  }, [map, onFound]);

  return null;
}
