# Next.js Migration Guide

This guide documents the step-by-step process for migrating from Streamlit to Next.js + React.

## 🎯 Migration Strategy Overview

1. **Current State**: Streamlit app running (unchanged)
2. **Phase 1**: FastAPI backend extraction (✅ COMPLETE on `feature/fastapi-backend` branch)
3. **Phase 2**: Next.js frontend development (separate repository)
4. **Phase 3**: Parallel operation (both UIs available)
5. **Phase 4**: Gradual user migration

## 📁 Repository Structure

```
strava-tracks-analyzer/         # This repo
├── api/                       # FastAPI backend (NEW)
│   ├── main.py               # API endpoints
│   └── __init__.py
├── core/                      # Algorithms (unchanged)
├── services/                  # Business logic (reusable)
├── adapters/                  # State management (framework-agnostic)
└── app.py                     # Streamlit UI (keeps running)

foil-lab-web/                  # New repo (to be created)
├── src/
│   ├── components/           # React components
│   ├── pages/               # Next.js pages
│   └── lib/                 # API client
└── public/                   # Static assets
```

## 🚀 Phase 1: FastAPI Backend (COMPLETE)

### What We've Built

✅ **API Endpoints**:
- `GET /` - API information
- `GET /api/health` - Health check
- `POST /api/analyze-track` - Full track analysis
- `POST /api/estimate-wind` - Wind direction estimation

✅ **Key Features**:
- Uses memory state adapters (no UI dependencies)
- CORS enabled for frontend access
- Pydantic models for type safety
- Same algorithms as Streamlit app

### Testing the API

1. **Start the API server**:
```bash
cd strava-tracks-analyzer
source venv/bin/activate
python run_api.py
```

2. **Test with curl**:
```bash
# Health check
curl http://localhost:8000/api/health

# Analyze a track
curl -X POST "http://localhost:8000/api/analyze-track" \
  -F "file=@data/test_file_270_degrees.gpx" \
  -F "wind_direction=270"
```

3. **View API documentation**:
   Open http://localhost:8000/docs in your browser

## 🎨 Phase 2: Next.js Frontend Development

### Step 1: Create Next.js Project

```bash
# Create new repository
mkdir foil-lab-web
cd foil-lab-web
git init

# Initialize Next.js with TypeScript and Tailwind
npx create-next-app@latest . --typescript --tailwind --app \
  --no-src-dir --import-alias "@/*"

# Install additional dependencies
npm install axios recharts react-leaflet leaflet @types/leaflet
npm install react-dropzone lucide-react class-variance-authority
npm install @radix-ui/react-slider @radix-ui/react-dialog
npm install clsx tailwind-merge
```

### Step 2: Project Structure

```
foil-lab-web/
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx            # Home page
│   ├── analysis/
│   │   └── page.tsx        # Track analysis page
│   └── comparison/
│       └── page.tsx        # Gear comparison page
├── components/
│   ├── ui/                 # Shadcn/ui components
│   ├── FileUpload.tsx      # GPX file upload
│   ├── ParameterControls.tsx # Wind direction, etc.
│   ├── PolarPlot.tsx       # Performance polar
│   ├── TrackMap.tsx        # Interactive map
│   └── SegmentTable.tsx    # Segment analysis
├── lib/
│   ├── api.ts             # API client
│   └── types.ts           # TypeScript types
└── styles/
    └── globals.css         # Global styles
```

### Step 3: API Client Setup

```typescript
// lib/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

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
) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/api/analyze-track', formData, {
    params,
  });
  
  return response.data;
}
```

### Step 4: Core Components

**File Upload Component**:
```typescript
// components/FileUpload.tsx
'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2 } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
}

export function FileUpload({ onFileSelect, isLoading }: FileUploadProps) {
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
        transition-colors duration-200
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
        ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:border-gray-400'}
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center space-y-2">
        {isLoading ? (
          <Loader2 className="h-12 w-12 text-gray-400 animate-spin" />
        ) : (
          <Upload className="h-12 w-12 text-gray-400" />
        )}
        <p className="text-lg font-medium">
          {isDragActive ? 'Drop the GPX file here' : 'Drag & drop a GPX file here'}
        </p>
        <p className="text-sm text-gray-500">or click to select</p>
      </div>
    </div>
  );
}
```

**Parameter Controls**:
```typescript
// components/ParameterControls.tsx
'use client';

import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';

interface ParameterControlsProps {
  windDirection: number;
  onWindDirectionChange: (value: number) => void;
  angleTolerance: number;
  onAngleToleranceChange: (value: number) => void;
  // ... other parameters
}

export function ParameterControls({
  windDirection,
  onWindDirectionChange,
  angleTolerance,
  onAngleToleranceChange,
}: ParameterControlsProps) {
  return (
    <div className="space-y-6 p-6 bg-white rounded-lg shadow">
      <h3 className="text-lg font-semibold">Analysis Parameters</h3>
      
      <div className="space-y-2">
        <div className="flex justify-between">
          <Label htmlFor="wind-direction">Wind Direction</Label>
          <span className="text-sm font-medium">{windDirection}°</span>
        </div>
        <Slider
          id="wind-direction"
          value={[windDirection]}
          onValueChange={(value) => onWindDirectionChange(value[0])}
          max={359}
          step={1}
          className="w-full"
        />
        <p className="text-xs text-gray-500">
          Direction the wind is coming FROM (0° = North)
        </p>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between">
          <Label htmlFor="angle-tolerance">Angle Tolerance</Label>
          <span className="text-sm font-medium">{angleTolerance}°</span>
        </div>
        <Slider
          id="angle-tolerance"
          value={[angleTolerance]}
          onValueChange={(value) => onAngleToleranceChange(value[0])}
          min={5}
          max={45}
          step={1}
          className="w-full"
        />
      </div>
    </div>
  );
}
```

### Step 5: Main Analysis Page

```typescript
// app/analysis/page.tsx
'use client';

import { useState } from 'react';
import { FileUpload } from '@/components/FileUpload';
import { ParameterControls } from '@/components/ParameterControls';
import { PolarPlot } from '@/components/PolarPlot';
import { TrackMap } from '@/components/TrackMap';
import { analyzeTrack } from '@/lib/api';

export default function AnalysisPage() {
  const [windDirection, setWindDirection] = useState(90);
  const [angleTolerance, setAngleTolerance] = useState(25);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleFileSelect = async (file: File) => {
    setIsLoading(true);
    try {
      const result = await analyzeTrack(file, {
        wind_direction: windDirection,
        angle_tolerance: angleTolerance,
      });
      setAnalysisResult(result);
    } catch (error) {
      console.error('Analysis failed:', error);
      // Handle error
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Track Analysis</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <FileUpload onFileSelect={handleFileSelect} isLoading={isLoading} />
          
          {analysisResult && (
            <div className="mt-8 space-y-8">
              <TrackMap segments={analysisResult.segments} />
              <PolarPlot segments={analysisResult.segments} />
            </div>
          )}
        </div>
        
        <div>
          <ParameterControls
            windDirection={windDirection}
            onWindDirectionChange={setWindDirection}
            angleTolerance={angleTolerance}
            onAngleToleranceChange={setAngleTolerance}
          />
        </div>
      </div>
    </div>
  );
}
```

## 🚀 Phase 3: Deployment

### Backend Deployment (Railway/Render)

1. **Update requirements.txt** (already done)
2. **Create Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

3. **Deploy to Railway**:
   - Connect GitHub repo
   - Set Python buildpack
   - Environment variables if needed

### Frontend Deployment (Vercel)

1. **Push to GitHub**
2. **Connect to Vercel**
3. **Set environment variable**:
   ```
   NEXT_PUBLIC_API_URL=https://foil-lab-api.railway.app
   ```

## 📋 Development Checklist

### Week 1: Core Functionality
- [ ] File upload and analysis
- [ ] Parameter controls
- [ ] Basic results display
- [ ] Error handling

### Week 2: Visualizations
- [ ] Polar performance plot
- [ ] Interactive track map
- [ ] Segment table
- [ ] Performance metrics cards

### Week 3: Polish
- [ ] Loading states
- [ ] Animations
- [ ] Mobile responsiveness
- [ ] Dark mode support

### Week 4: Advanced Features
- [ ] Gear comparison page
- [ ] Session history
- [ ] Export functionality
- [ ] User preferences

## 🎯 Success Metrics

1. **Feature Parity**: All Streamlit features work in Next.js
2. **Performance**: Page loads < 2 seconds
3. **Mobile**: Works on phones/tablets
4. **User Feedback**: Beta users prefer new UI

## 🔗 Resources

- **Next.js Docs**: https://nextjs.org/docs
- **Shadcn/ui**: https://ui.shadcn.com/
- **Recharts**: https://recharts.org/
- **React-Leaflet**: https://react-leaflet.js.org/
- **Tailwind CSS**: https://tailwindcss.com/

## 💡 Tips

1. **Start Simple**: Get basic upload → analysis → display working first
2. **Iterate**: Ship early, get feedback, improve
3. **Responsive First**: Design for mobile from the start
4. **Type Safety**: Use TypeScript everywhere
5. **Component Library**: Use Shadcn/ui for consistent design

---

This migration guide will evolve as we progress. Update it with learnings and decisions!