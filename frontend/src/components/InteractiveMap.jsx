import React, { useState } from 'react'
import Map, { NavigationControl, FullscreenControl, ScaleControl, Marker, Popup, Source, Layer } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapboxLocateControl } from './MapboxLocateControl'
import { MapboxGeocoderControl } from './MapboxGeocoder'

import { MAPBOX_TOKEN } from '../config/map'

export { Marker, Popup, Source, Layer };

export const InteractiveMap = ({ 
  children, 
  initialViewState, 
  onLocationSelect, 
  showGeocoder = true,
  showLocate = true,
  mapStyle = "mapbox://styles/mapbox/light-v11",
  ...props 
}) => {
  const [viewState, setViewState] = useState(initialViewState || {
    longitude: 77.5946,
    latitude: 12.9716,
    zoom: 12
  });

  return (
    <Map
      {...viewState}
      onMove={evt => setViewState(evt.viewState)}
      style={{ width: '100%', height: '100%' }}
      mapStyle={mapStyle}
      mapboxAccessToken={MAPBOX_TOKEN}
      {...props}
    >
      {showLocate && <MapboxLocateControl onFound={onLocationSelect} />}
      {showGeocoder && <MapboxGeocoderControl mapboxAccessToken={MAPBOX_TOKEN} onFound={onLocationSelect} />}
      
      <NavigationControl position="bottom-right" />
      <FullscreenControl position="bottom-right" />
      <ScaleControl position="bottom-left" />
      
      {children}
    </Map>
  )
}

export default InteractiveMap
