import MapboxDraw from '@mapbox/mapbox-gl-draw';
import { useControl } from 'react-map-gl';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';

export default function MapboxDrawControl(props) {
  useControl(
    () => new MapboxDraw(props),
    ({ map }) => {
      map.on('draw.create', props.onCreate);
      map.on('draw.update', props.onUpdate);
      map.on('draw.delete', props.onDelete);
      
      const addInitialData = () => {
        const draw = map._controls.find(c => c instanceof MapboxDraw);
        if (draw && props.initialData) {
            draw.add(props.initialData);
        }
      };

      if (map.loaded()) {
        addInitialData();
      } else {
        map.on('load', addInitialData);
      }
    },
    ({ map }) => {
      map.off('draw.create', props.onCreate);
      map.off('draw.update', props.onUpdate);
      map.off('draw.delete', props.onDelete);
    },
    {
      position: props.position
    }
  );

  return null;
}
