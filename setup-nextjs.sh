#!/bin/bash

# Setup script for Foil Lab Next.js frontend
# Run this from inside the foil-lab-web directory

echo "🚀 Setting up Foil Lab Next.js frontend..."

# Check if we're in the right directory
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository. Please run from foil-lab-web directory"
    exit 1
fi

# Initialize Next.js project
echo "📦 Creating Next.js app..."
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --import-alias "@/*" --yes

# Install additional dependencies
echo "📦 Installing additional dependencies..."
npm install axios react-dropzone lucide-react clsx tailwind-merge

# Create directories
echo "📁 Creating directories..."
mkdir -p lib components app/analyze

# Create .env.local
echo "🔧 Creating environment variables..."
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=https://strava-tracks-analyzer-production.up.railway.app
EOF

# Create lib/api.ts
echo "📝 Creating API client..."
cat > lib/api.ts << 'EOF'
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
});

export interface WindEstimate {
  direction: number;
  confidence: string;
  port_average_angle: number;
  starboard_average_angle: number;
  total_segments: number;
  port_segments: number;
  starboard_segments: number;
}

export interface PerformanceMetrics {
  avg_speed: number | null;
  avg_upwind_angle: number | null;
  best_upwind_angle: number | null;
  vmg_upwind: number | null;
  vmg_downwind: number | null;
  port_tack_count: number;
  starboard_tack_count: number;
}

export interface TrackSummary {
  total_distance: number;
  duration_seconds: number;
  avg_speed_knots: number;
  max_speed_knots: number;
  filename: string;
}

export interface AnalysisResult {
  segments: any[];
  wind_estimate: WindEstimate;
  performance_metrics: PerformanceMetrics;
  track_summary: TrackSummary;
}

export async function analyzeTrack(
  file: File,
  params: {
    wind_direction: number;
    angle_tolerance?: number;
    min_duration?: number;
    min_distance?: number;
    min_speed?: number;
    suspicious_angle_threshold?: number;
  }
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append('file', file);

  const queryParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      queryParams.append(key, value.toString());
    }
  });

  const response = await api.post<AnalysisResult>(
    `/api/analyze-track?${queryParams.toString()}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}
EOF

# Create components/FileUpload.tsx
echo "📝 Creating FileUpload component..."
cat > components/FileUpload.tsx << 'EOF'
'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Loader2 } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  selectedFile?: File | null;
}

export function FileUpload({ onFileSelect, isLoading, selectedFile }: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/gpx+xml': ['.gpx'],
    },
    multiple: false,
    disabled: isLoading,
  });

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
        transition-all duration-200
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white'}
        ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:border-gray-400'}
        ${selectedFile ? 'bg-green-50 border-green-300' : ''}
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center space-y-2">
        {isLoading ? (
          <>
            <Loader2 className="h-12 w-12 text-gray-400 animate-spin" />
            <p className="text-lg font-medium">Analyzing track...</p>
          </>
        ) : selectedFile ? (
          <>
            <FileText className="h-12 w-12 text-green-600" />
            <p className="text-lg font-medium text-green-600">
              {selectedFile.name}
            </p>
            <p className="text-sm text-gray-500">
              Click or drop a new file to change
            </p>
          </>
        ) : (
          <>
            <Upload className="h-12 w-12 text-gray-400" />
            <p className="text-lg font-medium">
              {isDragActive ? 'Drop the GPX file here' : 'Drag & drop a GPX file here'}
            </p>
            <p className="text-sm text-gray-500">or click to select</p>
          </>
        )}
      </div>
    </div>
  );
}
EOF

# Create components/AnalysisResults.tsx
echo "📝 Creating AnalysisResults component..."
cat > components/AnalysisResults.tsx << 'EOF'
'use client';

import { AnalysisResult } from '@/lib/api';

interface AnalysisResultsProps {
  result: AnalysisResult;
}

export function AnalysisResults({ result }: AnalysisResultsProps) {
  const metrics = result.performance_metrics;
  const windEstimate = result.wind_estimate;
  const summary = result.track_summary;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Segments"
          value={result.segments.length}
          unit=""
          color="blue"
        />
        <MetricCard
          label="Wind Direction"
          value={windEstimate.direction.toFixed(0)}
          unit="°"
          subtext={`Confidence: ${windEstimate.confidence}`}
          color="green"
        />
        <MetricCard
          label="VMG Upwind"
          value={metrics.vmg_upwind?.toFixed(1) || 'N/A'}
          unit="kn"
          color="purple"
        />
        <MetricCard
          label="Avg Speed"
          value={summary.avg_speed_knots.toFixed(1)}
          unit="kn"
          subtext={`Max: ${summary.max_speed_knots.toFixed(1)} kn`}
          color="orange"
        />
      </div>

      {/* Performance Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Performance Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Upwind Performance</h4>
            <dl className="space-y-2">
              <div className="flex justify-between">
                <dt className="text-gray-600">Best Upwind Angle:</dt>
                <dd className="font-medium">
                  {metrics.best_upwind_angle?.toFixed(0) || 'N/A'}°
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Avg Upwind Angle:</dt>
                <dd className="font-medium">
                  {metrics.avg_upwind_angle?.toFixed(0) || 'N/A'}°
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Port Tacks:</dt>
                <dd className="font-medium">{metrics.port_tack_count}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Starboard Tacks:</dt>
                <dd className="font-medium">{metrics.starboard_tack_count}</dd>
              </div>
            </dl>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Session Summary</h4>
            <dl className="space-y-2">
              <div className="flex justify-between">
                <dt className="text-gray-600">Total Distance:</dt>
                <dd className="font-medium">
                  {summary.total_distance.toFixed(1)} km
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Duration:</dt>
                <dd className="font-medium">
                  {Math.floor(summary.duration_seconds / 60)} min
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Avg Speed:</dt>
                <dd className="font-medium">
                  {metrics.avg_speed?.toFixed(1) || summary.avg_speed_knots.toFixed(1)} kn
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      {/* Wind Estimation Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Wind Analysis</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {windEstimate.port_segments}
            </p>
            <p className="text-sm text-gray-600">Port Segments</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">
              {windEstimate.starboard_segments}
            </p>
            <p className="text-sm text-gray-600">Starboard Segments</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-600">
              {windEstimate.port_average_angle.toFixed(0)}°
            </p>
            <p className="text-sm text-gray-600">Port Avg Angle</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-orange-600">
              {windEstimate.starboard_average_angle.toFixed(0)}°
            </p>
            <p className="text-sm text-gray-600">Starboard Avg Angle</p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  unit: string;
  subtext?: string;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

function MetricCard({ label, value, unit, subtext, color }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    orange: 'bg-orange-50 text-orange-700',
  };

  return (
    <div className={`rounded-lg p-6 ${colorClasses[color]}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="text-3xl font-bold mt-1">
        {value}
        <span className="text-xl ml-1">{unit}</span>
      </p>
      {subtext && <p className="text-xs mt-1 opacity-70">{subtext}</p>}
    </div>
  );
}
EOF

# Create app/page.tsx
echo "📝 Creating home page..."
cat > app/page.tsx << 'EOF'
import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold mb-6 text-gray-900">
            🪂 Foil Lab
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Analyze your wingfoil sessions with advanced wind and performance metrics
          </p>
          <div className="space-y-4">
            <Link
              href="/analyze"
              className="inline-block bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              Start Analysis
            </Link>
            <p className="text-sm text-gray-500">
              Upload a GPX file to get started
            </p>
          </div>
          
          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="font-semibold text-lg mb-2">📊 Track Analysis</h3>
              <p className="text-gray-600">
                Automatic segment detection and wind direction estimation
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="font-semibold text-lg mb-2">💨 VMG Calculation</h3>
              <p className="text-gray-600">
                Distance-weighted velocity made good for accurate performance metrics
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="font-semibold text-lg mb-2">📈 Performance Metrics</h3>
              <p className="text-gray-600">
                Detailed analysis of your upwind angles and speed
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
EOF

# Create app/layout.tsx
echo "📝 Creating layout..."
cat > app/layout.tsx << 'EOF'
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Foil Lab - Wingfoil Track Analysis",
  description: "Analyze your wingfoil sessions with advanced wind and performance metrics",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-white shadow-sm border-b">
          <div className="container mx-auto px-4">
            <div className="flex justify-between items-center h-16">
              <a href="/" className="text-xl font-bold text-gray-900">
                🪂 Foil Lab
              </a>
              <div className="text-sm text-gray-500">
                Beta Version
              </div>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
EOF

# Create app/analyze/page.tsx
echo "📝 Creating analysis page..."
cat > app/analyze/page.tsx << 'EOF'
'use client';

import { useState } from 'react';
import { FileUpload } from '@/components/FileUpload';
import { AnalysisResults } from '@/components/AnalysisResults';
import { analyzeTrack, AnalysisResult } from '@/lib/api';
import { AlertCircle } from 'lucide-react';

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Parameters
  const [windDirection, setWindDirection] = useState(90);
  const [angleTolerance, setAngleTolerance] = useState(25);
  const [minDuration, setMinDuration] = useState(10);
  const [minDistance, setMinDistance] = useState(50);

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setError(null);
    setResult(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const analysisResult = await analyzeTrack(file, {
        wind_direction: windDirection,
        angle_tolerance: angleTolerance,
        min_duration: minDuration,
        min_distance: minDistance,
      });
      setResult(analysisResult);
    } catch (err: any) {
      console.error('Analysis failed:', err);
      setError(
        err.response?.data?.detail || 
        'Analysis failed. Please check your file and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Track Analysis</h1>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column - File Upload and Parameters */}
            <div className="lg:col-span-1 space-y-6">
              <FileUpload 
                onFileSelect={handleFileSelect} 
                isLoading={loading}
                selectedFile={file}
              />
              
              {/* Parameters */}
              <div className="bg-white rounded-lg shadow p-6 space-y-4">
                <h3 className="font-semibold text-lg mb-2">Analysis Parameters</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Wind Direction: {windDirection}°
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="359"
                    value={windDirection}
                    onChange={(e) => setWindDirection(Number(e.target.value))}
                    className="w-full"
                    disabled={loading}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Direction the wind is coming FROM (0° = North)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Angle Tolerance: {angleTolerance}°
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="45"
                    value={angleTolerance}
                    onChange={(e) => setAngleTolerance(Number(e.target.value))}
                    className="w-full"
                    disabled={loading}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Min Duration: {minDuration}s
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="60"
                    value={minDuration}
                    onChange={(e) => setMinDuration(Number(e.target.value))}
                    className="w-full"
                    disabled={loading}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Min Distance: {minDistance}m
                  </label>
                  <input
                    type="range"
                    min="20"
                    max="200"
                    step="10"
                    value={minDistance}
                    onChange={(e) => setMinDistance(Number(e.target.value))}
                    className="w-full"
                    disabled={loading}
                  />
                </div>

                <button
                  onClick={handleAnalyze}
                  disabled={!file || loading}
                  className={`
                    w-full py-3 px-4 rounded-lg font-medium transition-colors
                    ${!file || loading 
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                      : 'bg-blue-600 text-white hover:bg-blue-700'}
                  `}
                >
                  {loading ? 'Analyzing...' : 'Analyze Track'}
                </button>
              </div>
            </div>

            {/* Right Column - Results */}
            <div className="lg:col-span-2">
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start">
                  <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                  <p className="text-red-800">{error}</p>
                </div>
              )}
              
              {result ? (
                <AnalysisResults result={result} />
              ) : !loading && (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                  <p className="text-gray-500">
                    Upload a GPX file and click "Analyze Track" to see results
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
EOF

# Create git branch
echo "🌿 Creating git branch..."
git checkout -b feature/initial-ui
git add .
git commit -m "Initial Next.js setup with track analysis"

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Run: npm run dev"
echo "2. Visit: http://localhost:3000"
echo "3. Test with a GPX file!"
echo ""
echo "To deploy to Vercel:"
echo "1. Create GitHub repo: foil-lab-web"
echo "2. Push this branch: git push -u origin feature/initial-ui"
echo "3. Connect to Vercel.com"