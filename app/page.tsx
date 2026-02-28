'use client';

import { useState, useEffect } from 'react';

interface HealthCheckResponse {
  status: string;
  service: string;
}

export default function Home() {
  const [data, setData] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/health`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Health check failed with status ${response.status}`);
        }

        const result: HealthCheckResponse = await response.json();
        setData(result);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to check health status'
        );
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-white mb-2">
              Cloud-Native Code Judge
            </h1>
            <p className="text-slate-400">Backend Health Check</p>
          </div>

          {/* Health Check Card */}
          <div className="bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-700">
            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-slate-600 border-t-blue-500 rounded-full animate-spin"></div>
                  <p className="text-slate-300 font-medium">Checking health status...</p>
                </div>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div className="space-y-4">
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <p className="text-red-400 font-semibold">Error</p>
                  <p className="text-red-300 text-sm mt-1">{error}</p>
                </div>
                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Success State */}
            {data && !loading && !error && (
              <div className="space-y-6">
                {/* Status Badge */}
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-green-400 font-semibold">Service Healthy</span>
                </div>

                {/* Response Data */}
                <div className="bg-slate-900 rounded-lg p-6 border border-slate-700">
                  <h2 className="text-slate-300 font-semibold mb-4 text-sm uppercase tracking-wide">
                    Response
                  </h2>
                  <pre className="text-slate-200 text-sm font-mono overflow-x-auto">
                    <code>{JSON.stringify(data, null, 2)}</code>
                  </pre>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                    <p className="text-slate-400 text-sm mb-1">Status</p>
                    <p className="text-white font-semibold">
                      {data.status.charAt(0).toUpperCase() + data.status.slice(1)}
                    </p>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                    <p className="text-slate-400 text-sm mb-1">Service</p>
                    <p className="text-white font-semibold">{data.service}</p>
                  </div>
                </div>

                {/* Actions */}
                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Refresh
                </button>
              </div>
            )}
          </div>

          {/* Footer Info */}
          <div className="mt-8 text-center text-slate-400 text-sm">
            <p>API Endpoint: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</p>
          </div>
        </div>
      </div>
    </main>
  );
}
