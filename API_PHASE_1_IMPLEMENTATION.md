# API Phase 1: Backend Support for React Foundation

## Overview
Backend changes to support React Phase 1, maintaining full backward compatibility with Streamlit.

## Stage 1.A: CORS and File Upload Enhancements (Day 1-2)
**Branch**: `feature/react-migration-api-enhancements`

### Tasks:
1. **Enhanced CORS configuration**
   ```python
   # api/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000", "https://*.vercel.app"],
       allow_methods=["*"],
       allow_headers=["*"],
       expose_headers=["X-Process-ID", "X-Cache-Status"]
   )
   ```

2. **Streaming file upload endpoint**
   ```python
   @app.post("/api/upload/stream")
   async def upload_stream(
       file: UploadFile = File(...),
       background_tasks: BackgroundTasks
   ):
       # Return process ID immediately
       process_id = str(uuid.uuid4())
       background_tasks.add_task(process_file, file, process_id)
       return {"process_id": process_id}
   ```

3. **Upload progress endpoint**
   ```python
   @app.get("/api/upload/progress/{process_id}")
   async def get_progress(process_id: str):
       return {
           "status": upload_status.get(process_id, "unknown"),
           "progress": upload_progress.get(process_id, 0),
           "error": upload_errors.get(process_id)
       }
   ```

### Testable Outcomes:
- [ ] React app can upload files without CORS errors
- [ ] Progress endpoint returns real-time status
- [ ] Large files (>10MB) upload successfully
- [ ] Errors are properly reported

### Testing:
```bash
# Test CORS
curl -X OPTIONS http://localhost:8000/api/upload/stream \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"

# Test streaming upload
python test_streaming_upload.py
```

---

## Stage 1.B: Granular Analysis Endpoints (Day 3-4)
**Branch**: `feature/granular-endpoints`

### Tasks:
1. **Split analysis into components**
   ```python
   # Segments endpoint
   @app.get("/api/tracks/{track_id}/segments")
   async def get_segments(track_id: str):
       # Return just segments data
       pass
   
   # Performance stats endpoint  
   @app.get("/api/tracks/{track_id}/stats")
   async def get_stats(track_id: str):
       # Return just statistics
       pass
   
   # Wind analysis endpoint
   @app.get("/api/tracks/{track_id}/wind")
   async def get_wind_analysis(track_id: str):
       # Return wind estimation details
       pass
   ```

2. **Add caching headers**
   ```python
   from fastapi import Response
   
   @app.get("/api/tracks/{track_id}/segments")
   async def get_segments(track_id: str, response: Response):
       segments = get_cached_segments(track_id)
       if segments:
           response.headers["X-Cache-Status"] = "HIT"
       else:
           segments = calculate_segments(track_id)
           response.headers["X-Cache-Status"] = "MISS"
       return segments
   ```

### Testable Outcomes:
- [ ] Each endpoint returns focused data
- [ ] Cache headers indicate hit/miss
- [ ] Response times <100ms for cached data
- [ ] Endpoints can be called independently

### Testing:
```bash
# Test individual endpoints
./test_endpoints.sh

# Verify caching
python test_cache_behavior.py
```

---

## Stage 1.C: Parameter Update Endpoint (Day 5-6)
**Branch**: `feature/parameter-updates`

### Tasks:
1. **Create parameter update endpoint**
   ```python
   @app.patch("/api/tracks/{track_id}/parameters")
   async def update_parameters(
       track_id: str,
       params: ParameterUpdate,
       background_tasks: BackgroundTasks
   ):
       # Validate which components need recalculation
       affected = determine_affected_components(params)
       
       # Queue recalculation
       if affected:
           background_tasks.add_task(
               recalculate_components,
               track_id,
               params,
               affected
           )
       
       return {
           "track_id": track_id,
           "affected_components": affected,
           "status": "processing"
       }
   ```

2. **Implement smart recalculation**
   ```python
   def determine_affected_components(params: ParameterUpdate) -> List[str]:
       affected = []
       
       if params.wind_direction is not None:
           affected.extend(["wind_angles", "vmg", "stats"])
       
       if any([params.angle_tolerance, params.min_distance]):
           affected.extend(["segments", "vmg", "stats"])
       
       return list(set(affected))
   ```

### Testable Outcomes:
- [ ] Wind changes only recalculate dependent components
- [ ] Parameter validation returns clear errors
- [ ] Background processing doesn't block response
- [ ] Partial updates work correctly

### Testing:
```bash
# Test parameter updates
python test_parameter_updates.py

# Verify minimal recalculation
python verify_smart_recalc.py
```

---

## Stage 1.D: Error Handling Enhancement (Day 7-8)
**Branch**: `feature/error-handling`

### Tasks:
1. **Structured error responses**
   ```python
   class APIError(Exception):
       def __init__(self, code: str, message: str, details: dict = None):
           self.code = code
           self.message = message
           self.details = details or {}
   
   @app.exception_handler(APIError)
   async def api_error_handler(request: Request, exc: APIError):
       return JSONResponse(
           status_code=400,
           content={
               "error": {
                   "code": exc.code,
                   "message": exc.message,
                   "details": exc.details
               }
           }
       )
   ```

2. **Validation with helpful messages**
   ```python
   def validate_gpx_file(file_content: bytes):
       if len(file_content) > 50 * 1024 * 1024:  # 50MB
           raise APIError(
               code="FILE_TOO_LARGE",
               message="File size exceeds 50MB limit",
               details={
                   "max_size_mb": 50,
                   "actual_size_mb": len(file_content) / 1024 / 1024
               }
           )
   ```

### Testable Outcomes:
- [ ] All errors return consistent format
- [ ] Error messages are actionable
- [ ] Validation errors include field details
- [ ] 5XX errors are properly logged

### Testing:
```bash
# Test error scenarios
python test_error_handling.py

# Verify error format
curl -X POST http://localhost:8000/api/analyze-track \
  -F "file=@invalid.txt" | jq
```

---

## Stage 1.E: Performance Monitoring (Day 9-10)
**Branch**: `feature/monitoring`

### Tasks:
1. **Add request timing**
   ```python
   import time
   from fastapi import Request
   
   @app.middleware("http")
   async def add_process_time_header(request: Request, call_next):
       start_time = time.time()
       response = await call_next(request)
       process_time = time.time() - start_time
       response.headers["X-Process-Time"] = str(process_time)
       return response
   ```

2. **Health check with details**
   ```python
   @app.get("/api/health/detailed")
   async def health_detailed():
       return {
           "status": "healthy",
           "version": API_VERSION,
           "cache": {
               "enabled": CACHE_ENABLED,
               "hit_rate": calculate_cache_hit_rate()
           },
           "performance": {
               "avg_response_time": get_avg_response_time(),
               "active_requests": get_active_requests()
           }
       }
   ```

### Testable Outcomes:
- [ ] All responses include process time header
- [ ] Health endpoint shows real metrics
- [ ] Slow requests are logged (>1s)
- [ ] Memory usage is tracked

### Testing:
```bash
# Load test
locust -f loadtest.py --host=http://localhost:8000

# Monitor metrics
python monitor_performance.py
```

---

## Integration Testing

### API Test Suite
```bash
# Run all API tests
pytest tests/api/

# Run with coverage
pytest --cov=api tests/api/
```

### Backward Compatibility Tests
```bash
# Ensure Streamlit still works
python test_streamlit_compatibility.py
```

### Performance Benchmarks
```bash
# Baseline performance
python benchmark_api.py

# Target metrics:
# - P50 response time: <100ms
# - P95 response time: <500ms
# - Throughput: >100 req/s
```

---

## Deployment Checklist

Before deploying each stage:
- [ ] All tests passing
- [ ] No breaking changes to existing endpoints
- [ ] Performance benchmarks met
- [ ] Error handling tested
- [ ] Logging configured
- [ ] Documentation updated

---

## Rollback Plan

Each stage can be rolled back independently:
```bash
# Quick rollback
git revert HEAD
git push origin feature/[stage-name]

# Or use feature flags
ENABLE_STREAMING_UPLOAD=false
ENABLE_GRANULAR_ENDPOINTS=false
```

Ready to implement backend support for the React migration!