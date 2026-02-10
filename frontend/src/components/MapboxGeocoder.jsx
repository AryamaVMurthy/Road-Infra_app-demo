import { useControl } from 'react-map-gl';
import MapboxGeocoder from '@mapbox/mapbox-gl-geocoder';
import '@mapbox/mapbox-gl-geocoder/dist/mapbox-gl-geocoder.css';
import { MAPBOX_TOKEN } from '../config/map';

export function MapboxGeocoderControl({ onFound, mapboxAccessToken = MAPBOX_TOKEN }) {
  useControl(
    () => {
      const ctrl = new MapboxGeocoder({
        accessToken: mapboxAccessToken,
        marker: false,
        collapsed: false,
        placeholder: 'Search address or area...'
      });
      
      ctrl.on('result', (e) => {
        const { center } = e.result;
        if (onFound) {
          onFound({ lat: center[1], lng: center[0] });
        }
      });
      
      return ctrl;
    },
    {
      position: 'top-left'
    }
  );

  return null;
}
