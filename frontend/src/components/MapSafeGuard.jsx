import React, { Component } from 'react';
import { AlertTriangle, Map as MapIcon, ShieldAlert } from 'lucide-react';

export class MapErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Map Crash caught by ErrorBoundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full w-full bg-slate-50 border-4 border-dashed border-slate-200 rounded-[3rem] p-12 text-center space-y-6">
          <div className="p-6 bg-rose-100 text-rose-600 rounded-full shadow-lg shadow-rose-200/50">
            <ShieldAlert size={48} />
          </div>
          <div className="space-y-2">
            <h3 className="text-2xl font-black text-slate-900">Map Interface Crashed</h3>
            <p className="text-slate-500 font-medium max-w-md mx-auto">
              The map engine encountered a critical error. This is usually due to an invalid Mapbox configuration or token.
            </p>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-100 text-left w-full max-w-lg overflow-auto">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Error Details</p>
            <code className="text-xs font-mono text-rose-500 break-all">{this.state.error?.message || 'Unknown Error'}</code>
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="px-8 py-4 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/20"
          >
            Attempt Re-sync
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export const isTokenValid = (token) => {
  if (!token) return false;
  if (token.includes('your_actual_token')) return false;
  if (token.includes('example')) return false;
  if (!token.startsWith('pk.')) return false;
  if (token.length < 30) return false;
  return true;
};

export const MapTokenGuard = ({ token, children }) => {
  if (!isTokenValid(token)) {
    return (
      <div className="flex flex-col items-center justify-center h-full w-full bg-slate-50 border-4 border-dashed border-slate-200 rounded-[3rem] p-12 text-center space-y-6">
        <div className="p-6 bg-amber-100 text-amber-600 rounded-full shadow-lg shadow-amber-200/50">
          <MapIcon size={48} />
        </div>
        <div className="space-y-2">
          <h3 className="text-2xl font-black text-slate-900">Mapbox Token Required</h3>
          <p className="text-slate-500 font-medium max-w-md mx-auto">
            The geospatial operations map requires a valid Mapbox Access Token. 
            The current token is either missing or set to a placeholder.
          </p>
        </div>
        <div className="flex flex-col gap-3 w-full max-w-md">
          <div className="bg-white p-4 rounded-2xl border border-slate-100 text-left">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Configuration Path</p>
            <code className="text-xs font-mono text-slate-700">frontend/.env.production</code>
            <p className="mt-2 text-[10px] font-bold text-slate-400">Set: VITE_MAPBOX_TOKEN=pk.xxx</p>
          </div>
          <a 
            href="https://account.mapbox.com/access-tokens/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="px-8 py-4 bg-primary text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-primary/90 transition-all shadow-xl shadow-primary/20"
          >
            Get Mapbox Token
          </a>
        </div>
      </div>
    );
  }

  return children;
};
