import Map from 'react-map-gl'

import { MAPBOX_STYLE, MAPBOX_TOKEN } from '../config/map'

export function BaseMap({ children, initialViewState, style, ...props }) {
  return (
    <Map
      initialViewState={initialViewState}
      style={style || { width: '100%', height: '100%' }}
      mapStyle={MAPBOX_STYLE}
      mapboxAccessToken={MAPBOX_TOKEN}
      {...props}
    >
      {children}
    </Map>
  )
}
