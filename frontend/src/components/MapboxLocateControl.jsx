import { useControl } from 'react-map-gl';
import { Navigation } from 'lucide-react';
import { renderToString } from 'react-dom/server';
import mapboxgl from 'mapbox-gl';

class LocateControl {
  constructor(onFound) {
    this.onFound = onFound;
  }

  onAdd(map) {
    this._map = map;
    this._container = document.createElement('div');
    this._container.className = 'mapboxgl-ctrl mapboxgl-ctrl-group';
    this._container.style.margin = '10px';

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

          this._map.flyTo({
            center: lngLat,
            zoom: 18,
            essential: true
          });

          if (this._marker) this._marker.remove();
          
          try {
              if (this._map.getLayer('location-circle')) this._map.removeLayer('location-circle');
              if (this._map.getSource('location-circle')) this._map.removeSource('location-circle');
          } catch (e) {}

          this._marker = new mapboxgl.Marker()
            .setLngLat(lngLat)
            .setPopup(new mapboxgl.Popup().setHTML('<p>You are here</p>'))
            .addTo(this._map);
          
          this._marker.togglePopup();

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

          this._map.addSource('location-circle', {
            type: 'geojson',
            data: {
              type: 'Feature',
              geometry: {
                type: 'Polygon',
                coordinates: [coords]
              }
            }
          });

          this._map.addLayer({
            id: 'location-circle',
            type: 'fill',
            source: 'location-circle',
            paint: {
              'fill-color': '#3B82F6',
              'fill-opacity': 0.2
            }
          });

          if (this.onFound) {
            this.onFound({ lat: latitude, lng: longitude });
          }
        },
        (error) => {
          console.error('Location error:', error.message);
          alert('Unable to retrieve your location');
        }
      );
    };

    this._container.appendChild(button);
    return this._container;
  }

  onRemove() {
    if (this._marker) this._marker.remove();
    if (this._container && this._container.parentNode) {
        this._container.parentNode.removeChild(this._container);
    }
    this._map = undefined;
  }
}

export function MapboxLocateControl({ onFound }) {
  useControl(() => new LocateControl(onFound), { position: 'top-right' });
  return null;
}
