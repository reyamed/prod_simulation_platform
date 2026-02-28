import docker
import requests
import time
from .config import settings

docker_client = docker.from_env()

ES_HOST = settings.es_host
ES_AUTH = (settings.es_user, settings.es_password)

def get_container(name: str):
    try:
        return docker_client.containers.get(name)
    except docker.errors.NotFound:
        print(f"Container {name} not found.")
        return None

def trigger_scenario_1_easy_grok():
    """
    Stage 1: Intentional grok parse failure in Logstash.
    The logs from billing_service are malformed. 
    The fix is for the user to update the Logstash pipeline or the Logstash parsing logic.
    For this scenario trigger, we ensure the index exists and logstash is running.
    There is no specific infrastructure sabotage required; the worker generates bad logs.
    """
    print("Triggered Stage 1: Easy Grok Parse Failure.")

def trigger_scenario_2_replicas():
    """
    Stage 2: Indices & Replicas (Cluster Yellow)
    We create an empty index with 1 replica, but there's only 1 node in our Docker setup.
    The cluster health goes Yellow. The player has to fix the routing allocation.
    """
    index_name = "transactions-2026.01"
    headers = {"Content-Type": "application/json"}
    payload = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "routing.allocation.total_shards_per_node": 1  # Force unassigned replica
            }
        }
    }
    try:
        # Ignore 400 if it already exists
        res = requests.put(f"{ES_HOST}/{index_name}", json=payload, auth=ES_AUTH)
        if res.status_code in [200, 201]:
            print("Successfully triggered Stage 2 (Yellow Cluster).")
    except Exception as e:
        print(f"Failed to trigger Stage 2: {e}")

def trigger_scenario_3_data_view():
    """
    Stage 3: Missing Data View (Log Visibility)
    The user can't search for 'frontend-logs-*' in Kibana Discover because there is no Data View (Index Pattern).
    The root cause is Kibana isn't aware of the index, but the data is safely there.
    """
    # Create the dummy index with data so that setting up the data view works perfectly.
    index_name = "frontend-logs-2026.01"
    headers = {"Content-Type": "application/json"}
    payload = {
        "timestamp": time.time(),
        "level": "INFO",
        "message": "Frontend app started successfully on port 3000.",
        "component": "ui"
    }
    try:
        requests.post(f"{ES_HOST}/{index_name}/_doc", json=payload, auth=ES_AUTH)
        print("Successfully triggered Stage 3 (Missing Data View).")
    except Exception as e:
        print(f"Failed to trigger Stage 3: {e}")

def trigger_scenario_4_hard_disk_watermark():
    """
    Stage 4: Simulate High Disk Watermark.
    We forcefully set the cluster routing allocation disk watermark settings to block writes.
    The user will see read-only index blocks and must reset the watermark settings.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "persistent": {
            "cluster.routing.allocation.disk.watermark.low": "1b",
            "cluster.routing.allocation.disk.watermark.high": "1b",
            "cluster.routing.allocation.disk.watermark.flood_stage": "1b",
            "cluster.info.update.interval": "1m"
        }
    }
    try:
        response = requests.put(f"{ES_HOST}/_cluster/settings", json=payload, auth=ES_AUTH)
        if response.status_code == 200:
            print("Successfully triggered Stage 2 (Disk Watermark read-only block).")
    except Exception as e:
        print(f"Failed to trigger Stage 2: {e}")

def validate_stage_1():
    """
    Validates if the user fixed the grok parse failure.
    We check if the billing service logs no longer have the '_grokparsefailure_billing' tag 
    in the latest documents.
    """
    query = {
        "query": {
            "bool": {
                "must": [{"match": {"log_type": "billing_service"}}],
                "must_not": [{"match": {"tags": "_grokparsefailure_billing"}}]
            }
        },
        "size": 5,
        "sort": [{"@timestamp": {"order": "desc"}}]
    }
    try:
        res = requests.post(f"{ES_HOST}/logstash-billing_service-*/_search", json=query, auth=ES_AUTH)
        if res.status_code == 200:
            data = res.json()
            hits = data.get("hits", {}).get("hits", [])
            if len(hits) > 0:
                print("Stage 1 Validated: User successfully fixed grok pattern.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_2():
    """
    Validates if the user fixed the Yellow cluster status caused by the replica shard.
    Checks if `routing.allocation.total_shards_per_node` was increased or `number_of_replicas` adjusted.
    """
    try:
        res = requests.get(f"{ES_HOST}/transactions-2026.01/_settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            index_settings = settings.get("transactions-2026.01", {}).get("settings", {}).get("index", {})
            routing = index_settings.get("routing", {}).get("allocation", {}).get("total_shards_per_node")
            replicas = index_settings.get("number_of_replicas")
            
            # The player either allowed >1 shards per node, or explicitly dropped replicas to 0
            if (routing and int(routing) > 1) or (replicas and int(replicas) == 0):
                print("Stage 2 Validated: Replicas or routing allocated properly.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_3():
    """
    Validates if the user created the Data View for `frontend-logs-*` in Kibana.
    In Elasticsearch 8.x, Kibana data views are stored in the `.kibana` system index.
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"type": "index-pattern"}},
                    {"wildcard": {"index-pattern.title": "*frontend-logs*"}}
                ]
            }
        }
    }
    try:
        # Search the `.kibana` index for the index-pattern
        res = requests.post(f"{ES_HOST}/.kibana*/_search", json=query, auth=ES_AUTH)
        if res.status_code == 200:
            hits = res.json().get("hits", {}).get("total", {}).get("value", 0)
            if hits > 0:
                print("Stage 3 Validated: Data View created successfully.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_4():
    """
    Validates if the user reverted the flood_stage watermark settings back to defaults.
    """
    try:
        res = requests.get(f"{ES_HOST}/_cluster/settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            flood_stage = settings.get("persistent", {}).get("cluster", {}).get("routing", {}).get("allocation", {}).get("disk", {}).get("watermark", {}).get("flood_stage")
            
            # If default or restored
            if not flood_stage or flood_stage != "1b":
                print("Stage 4 Validated: Watermark fixed.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False
