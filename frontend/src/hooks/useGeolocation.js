import { useState, useEffect, useCallback } from 'react';

// IIIT Hyderabad, Gachibowli - default fallback location
const IIIT_HYDERABAD = { lat: 17.4455, lng: 78.3489 };
const HYDERABAD_CENTER = IIIT_HYDERABAD;

// Geolocation options for high accuracy
const GEO_OPTIONS = {
  enableHighAccuracy: true,  // Use GPS if available (more accurate but slower)
  timeout: 15000,            // Wait up to 15 seconds for position
  maximumAge: 60000,         // Accept cached position up to 1 minute old
};

/**
 * Custom hook for geolocation with Hyderabad-specific defaults
 * 
 * @param {Object} options
 * @param {boolean} options.autoFetch - Automatically fetch location on mount (default: true)
 * @param {Object} options.fallback - Fallback coordinates if geolocation fails (default: Hyderabad center)
 * @param {boolean} options.watch - Continuously watch position changes (default: false)
 * 
 * @returns {Object} { position, error, loading, refresh, isSupported }
 */
export function useGeolocation({
  autoFetch = true,
  fallback = HYDERABAD_CENTER,
  watch = false,
} = {}) {
  const [position, setPosition] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(autoFetch);

  const isSupported = typeof navigator !== 'undefined' && 'geolocation' in navigator;

  const handleSuccess = useCallback((pos) => {
    setPosition({
      lat: pos.coords.latitude,
      lng: pos.coords.longitude,
      accuracy: pos.coords.accuracy,
      timestamp: pos.timestamp,
    });
    setError(null);
    setLoading(false);
  }, []);

  const handleError = useCallback((err) => {
    let errorMessage;
    switch (err.code) {
      case err.PERMISSION_DENIED:
        errorMessage = 'Location permission denied. Using Hyderabad center.';
        break;
      case err.POSITION_UNAVAILABLE:
        errorMessage = 'Location unavailable. Using Hyderabad center.';
        break;
      case err.TIMEOUT:
        errorMessage = 'Location request timed out. Using Hyderabad center.';
        break;
      default:
        errorMessage = 'Unknown error getting location. Using Hyderabad center.';
    }
    
    console.warn('Geolocation error:', errorMessage, err);
    setError(errorMessage);
    setPosition({ ...fallback, accuracy: null, timestamp: Date.now() });
    setLoading(false);
  }, [fallback]);

  const refresh = useCallback(() => {
    if (!isSupported) {
      setError('Geolocation not supported');
      setPosition({ ...fallback, accuracy: null, timestamp: Date.now() });
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(handleSuccess, handleError, GEO_OPTIONS);
  }, [isSupported, fallback, handleSuccess, handleError]);

  useEffect(() => {
    if (!autoFetch) return;

    if (!isSupported) {
      setError('Geolocation not supported by this browser');
      setPosition({ ...fallback, accuracy: null, timestamp: Date.now() });
      setLoading(false);
      return;
    }

    if (watch) {
      const watchId = navigator.geolocation.watchPosition(
        handleSuccess,
        handleError,
        GEO_OPTIONS
      );
      return () => navigator.geolocation.clearWatch(watchId);
    } else {
      navigator.geolocation.getCurrentPosition(handleSuccess, handleError, GEO_OPTIONS);
    }
  }, [autoFetch, watch, isSupported, fallback, handleSuccess, handleError]);

  return {
    position,
    error,
    loading,
    refresh,
    isSupported,
    isUsingFallback: error !== null,
  };
}

// Export constants for use in components
export { HYDERABAD_CENTER, GEO_OPTIONS };
