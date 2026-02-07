# Mapbox Migration Guide

## Overview

This application has been migrated from Leaflet to Mapbox GL JS for map rendering. All existing features have been preserved while switching to the Mapbox API.

## Setup Instructions

### 1. Get a Mapbox Access Token

1. Visit [https://account.mapbox.com/](https://account.mapbox.com/)
2. Sign up for a free account or log in
3. Navigate to your [Access Tokens page](https://account.mapbox.com/access-tokens/)
4. Copy your default public token or create a new one

### 2. Configure Environment Variables

1. Navigate to the `frontend` directory
2. Create a `.env` file (you can copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
3. Add your Mapbox token to the `.env` file:
   ```
   VITE_MAPBOX_TOKEN=pk.your_actual_mapbox_token_here
   ```

### 3. Install Dependencies

Run the following command in the `frontend` directory:

```bash
npm install
```

This will install:

- `mapbox-gl` - Core Mapbox GL JS library
- `react-map-gl` - React wrapper for Mapbox GL JS
- `@mapbox/mapbox-gl-geocoder` - Search/geocoding functionality

### 4. Start the Application

```bash
npm run dev
```

## What Changed

### Package Dependencies

**Removed:**

- `leaflet`
- `react-leaflet`
- `leaflet.heat`
- `leaflet-control-geocoder`

**Added:**

- `mapbox-gl` (^3.1.2)
- `react-map-gl` (^7.1.7)
- `@mapbox/mapbox-gl-geocoder` (^5.0.2)

### Component Mapping

| Old Component (Leaflet) | New Component (Mapbox)       |
| ----------------------- | ---------------------------- |
| `MapContainer`          | `Map` from `react-map-gl`    |
| `TileLayer`             | Built into Mapbox map styles |
| `HeatmapLayer`          | `MapboxHeatmap`              |
| `LocateControl`         | `MapboxLocateControl`        |
| `SearchField`           | `MapboxGeocoderControl`      |
| `Marker`                | `Marker` from `react-map-gl` |
| `Popup`                 | `Popup` from `react-map-gl`  |

### New Component Files

Created in `frontend/src/components/`:

- `MapboxHeatmap.jsx` - Heatmap visualization using Mapbox heatmap layers
- `MapboxLocateControl.jsx` - Geolocation control with custom styling
- `MapboxGeocoder.jsx` - Address search functionality

### Updated Files

- `frontend/src/App.jsx` - Changed CSS import
- `frontend/src/pages/AnalyticsDashboard.jsx`
- `frontend/src/pages/authority/AuthorityDashboard.jsx`
- `frontend/src/pages/citizen/MyReports.jsx`
- `frontend/src/pages/worker/WorkerHome.jsx`

## Features Preserved

All map functionality has been preserved:

- ✅ Interactive maps with zoom and pan
- ✅ Marker placement and popups
- ✅ Heatmap visualization
- ✅ Geolocation/current location control
- ✅ Address search and geocoding
- ✅ Custom map styling
- ✅ Responsive behavior

## Map Styles

The application now uses Mapbox's built-in street style:

```javascript
mapStyle = "mapbox://styles/mapbox/streets-v12";
```

You can customize this to use other Mapbox styles:

- `mapbox://styles/mapbox/light-v11` - Light theme
- `mapbox://styles/mapbox/dark-v11` - Dark theme
- `mapbox://styles/mapbox/satellite-v9` - Satellite imagery
- `mapbox://styles/mapbox/outdoors-v12` - Outdoor/terrain style

Or create your own custom style in Mapbox Studio.

## API Usage Notes

### Free Tier Limits

Mapbox free tier includes:

- 50,000 map loads per month
- 100,000 geocoding requests per month
- Plenty for development and small-scale production

### Performance Benefits

- Hardware-accelerated rendering with WebGL
- Better performance on mobile devices
- Smoother animations and transitions
- Advanced styling capabilities

## Troubleshooting

### Map not displaying

- Check that your Mapbox token is correctly set in `.env`
- Verify the token starts with `pk.`
- Ensure you've run `npm install` after updating package.json

### "Invalid token" error

- Verify your token is valid on the Mapbox dashboard
- Make sure the token has public scopes enabled
- Check that the environment variable is named `VITE_MAPBOX_TOKEN`

### Heatmap not showing

- Ensure heatmap data has the correct format: `[{ lat, lng, intensity }]`
- Check that points array has valid coordinates

## Support

For Mapbox-specific issues:

- [Mapbox Documentation](https://docs.mapbox.com/)
- [react-map-gl Documentation](https://visgl.github.io/react-map-gl/)

For application-specific issues, refer to the main project documentation.
