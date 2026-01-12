from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from routers import  health
from services.elasticsearch_service import ElasticsearchService
from config import settings
import uvicorn

app = FastAPI(
    title=settings.api_title,
    description="""
    ## Log Management Platform API
    
    A comprehensive API for managing, querying, and monitoring logs stored in Elasticsearch.
    
    ### Features:
    - **Log Management**: Create and index log entries
    - **Log Search**: Advanced search with filters (type, level, source, time range, full-text)
    - **Health Monitoring**: Check API and Elasticsearch cluster health
    - **Metrics**: Get statistics about log indices and storage
    
    ### Endpoints:
    - `/api/logs` - Log management and search
    - `/api/health` - Health checks
    - `/api/metrics` - Metrics and statistics
    
    ### Documentation:
    - Swagger UI: `/docs`
    - ReDoc: `/redoc`
    """,
    version=settings.api_version,
    debug=settings.debug,
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}}
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)

# Initialize Elasticsearch service
es_service = ElasticsearchService()

# Include routers 
app.include_router(health.router, prefix="/api/health", tags=["health"])

@app.on_event("startup")
async def startup_event():
    """Initialize Elasticsearch indices and database on startup"""
    await es_service.initialize_indices()


@app.get(
    "/",
    summary="API Root",
    description="Get API information and available endpoints",
    tags=["root"],
    response_description="API information including version and available endpoints"
)
async def root():
    """
    Root endpoint that provides API information and links to available endpoints.
    """
    return {
        "message": settings.api_title,
        "version": settings.api_version,
        "endpoints": {
            #"logs": "/api/logs",
            "health": "/api/health",
            #"metrics": "/api/metrics",
            #"users": "/api/users"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)