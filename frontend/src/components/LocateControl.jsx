import L from "leaflet";
import { useMap } from "react-leaflet";
import { useEffect } from "react";
import { Navigation } from "lucide-react";
import { renderToString } from "react-dom/server";

export function LocateControl({ onFound }) {
  const map = useMap();

  useEffect(() => {
    const control = L.control({ position: "topright" });

    control.onAdd = function () {
      const div = L.DomUtil.create("div", "leaflet-bar leaflet-control leaflet-control-custom");
      div.style.backgroundColor = "white";
      div.style.width = "34px";
      div.style.height = "34px";
      div.style.display = "flex";
      div.style.alignItems = "center";
      div.style.justifyContent = "center";
      div.style.cursor = "pointer";
      div.title = "Get Current Location";
      div.innerHTML = renderToString(<Navigation size={18} className="text-primary" />);
      
      div.onclick = function (e) {
        e.stopPropagation();
        map.locate({ setView: true, maxZoom: 18 });
      };
      return div;
    };

    const onLocationFound = (e) => {
        if (onFound) onFound(e.latlng);
        L.circle(e.latlng, e.accuracy).addTo(map);
        L.marker(e.latlng).addTo(map).bindPopup("You are here").openPopup();
    };

    const onLocationError = (e) => {
        console.error("Location error:", e.message);
    };

    map.on('locationfound', onLocationFound);
    map.on('locationerror', onLocationError);

    control.addTo(map);
    return () => {
        control.remove();
        map.off('locationfound', onLocationFound);
        map.off('locationerror', onLocationError);
    };
  }, [map, onFound]);

  return null;
}
