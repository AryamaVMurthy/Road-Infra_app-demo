import { MapboxGeocoderControl } from './MapboxGeocoder'
import { MapboxLocateControl } from './MapboxLocateControl'

export function MapControls({
  onFound,
  showLocate = true,
  showGeocoder = true,
}) {
  return (
    <>
      {showLocate ? <MapboxLocateControl onFound={onFound} /> : null}
      {showGeocoder ? <MapboxGeocoderControl onFound={onFound} /> : null}
    </>
  )
}
