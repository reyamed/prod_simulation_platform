from datetime import datetime
from typing import Optional, Dict, Any, List
from elasticsearch import AsyncElasticsearch
from models.log_model import LogEntry, LogQuery, LogType
from config import settings

class ElasticsearchService:
    def __init__(self):
        self.es_host = settings.elasticsearch_host
        self.client = AsyncElasticsearch(
            [self.es_host],
            request_timeout=settings.elasticsearch_request_timeout
        )
        self.index_prefix = settings.elasticsearch_index_prefix
    
    async def initialize_indices(self):
        """Create index templates and indices for different log types"""
        index_template = {
            "index_patterns": [f"{self.index_prefix}-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.refresh_interval": "5s"
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "log_type": {"type": "keyword"},
                        "message": {"type": "text", "analyzer": "standard"},
                        "source": {"type": "keyword"},
                        "metadata": {"type": "object", "enabled": True}
                    }
                }
            }
        }
        
        try:
            await self.client.indices.put_index_template(
                name="logs-template",
                body=index_template
            )
        except Exception as e:
            print(f"Warning: Could not create index template: {e}")
    
    def _get_index_name(self, log_type: LogType) -> str:
        """Generate index name based on log type and date"""
        date_str = datetime.now().strftime("%Y.%m.%d")
        return f"{self.index_prefix}-{log_type.value}-{date_str}"
    
    async def index_log(self, log_entry: LogEntry) -> Dict[str, Any]:
        """Index a log entry into Elasticsearch"""
        index_name = self._get_index_name(log_entry.log_type)
        doc = log_entry.dict()
        
        try:
            response = await self.client.index(
                index=index_name,
                document=doc
            )
            return response
        except Exception as e:
            raise Exception(f"Failed to index log: {str(e)}")
    
    async def search_logs(self, query: LogQuery) -> Dict[str, Any]:
        """Search logs based on query parameters"""
        must_clauses = []
        
        if query.log_type:
            must_clauses.append({"term": {"log_type": query.log_type.value}})
        
        if query.level:
            must_clauses.append({"term": {"level": query.level.value}})
        
        if query.source:
            must_clauses.append({"term": {"source": query.source}})
        
        if query.start_time or query.end_time:
            time_range = {}
            if query.start_time:
                time_range["gte"] = query.start_time.isoformat()
            if query.end_time:
                time_range["lte"] = query.end_time.isoformat()
            must_clauses.append({"range": {"timestamp": time_range}})
        
        if query.query_string:
            must_clauses.append({
                "query_string": {
                    "query": query.query_string,
                    "default_field": "message"
                }
            })
        
        search_body = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}]
                }
            },
            "size": query.size,
            "from": query.from_,
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        index_pattern = f"{self.index_prefix}-*"
        
        try:
            response = await self.client.search(
                index=index_pattern,
                body=search_body
            )
            
            return {
                "total": response["hits"]["total"]["value"],
                "logs": [hit["_source"] for hit in response["hits"]["hits"]],
                "took": response["took"]
            }
        except Exception as e:
            raise Exception(f"Failed to search logs: {str(e)}")
    
    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get Elasticsearch cluster health"""
        try:
            health = await self.client.cluster.health()
            return health
        except Exception as e:
            raise Exception(f"Failed to get cluster health: {str(e)}")
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics for all log indices"""
        try:
            stats = await self.client.indices.stats(index=f"{self.index_prefix}-*")
            return stats
        except Exception as e:
            raise Exception(f"Failed to get index stats: {str(e)}")
    
    async def close(self):
        """Close the Elasticsearch client"""
        await self.client.close()


