import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from services.elasticsearch_service import ElasticsearchService

logger = logging.getLogger(__name__)
router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    elasticsearch: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "elasticsearch": {
                    "status": "green",
                    "cluster_name": "docker-cluster",
                    "number_of_nodes": 1
                }
            }
        }

es_service = ElasticsearchService()

@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API and Elasticsearch connection",
    response_description="Health status with Elasticsearch cluster information",
    tags=["health"],
    status_code=status.HTTP_200_OK
)
async def health_check():
    """
    Check the health of the API and Elasticsearch connection.
    
    Returns:
    - **status**: Overall health status (healthy/unhealthy)
    - **elasticsearch**: Elasticsearch cluster information including:
      - Cluster status (green/yellow/red)
      - Cluster name
      - Number of nodes
    
    Use this endpoint for monitoring and load balancer health checks.
    """
    try:
        cluster_health = await es_service.get_cluster_health()
    except HTTPException:
        # Pass through HTTP errors that may already be well-formed
        raise
    except Exception as exc:
        logger.exception("Elasticsearch health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Elasticsearch connection failed"
        ) from exc

    # Defensive defaults so a partial response does not explode the handler
    return HealthResponse(
        status="healthy",
        elasticsearch={
            "status": cluster_health.get("status", "unknown"),
            "cluster_name": cluster_health.get("cluster_name", "unknown"),
            "number_of_nodes": cluster_health.get("number_of_nodes", 0)
        }
    )