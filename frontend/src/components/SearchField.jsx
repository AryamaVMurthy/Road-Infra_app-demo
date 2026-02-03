import L from "leaflet";
import "leaflet-control-geocoder/dist/Control.Geocoder.css";
import "leaflet-control-geocoder";
import { useMap } from "react-leaflet";
import { useEffect } from "react";

export function SearchField() {
  const map = useMap();

  useEffect(() => {
    const geocoder = L.Control.Geocoder.nominatim();
    const control = L.Control.geocoder({
      query: "",
      placeholder: "Search address or area...",
      defaultMarkGeocode: false,
      geocoder
    })
      .on("markgeocode", function (e) {
        const latlng = e.geocode.center;
        map.setView(latlng, 18);
        L.marker(latlng).addTo(map).bindPopup(e.geocode.name).openPopup();
      })
      .addTo(map);

    return () => {
      control.remove();
    };
  }, [map]);

  return null;
}
