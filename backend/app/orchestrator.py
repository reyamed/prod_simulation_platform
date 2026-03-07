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
    In Elasticsearch 8.x, Kibana data views are stored in the `.kibana` system index, 
    but querying them directly is flaky due to spaces. Instead, we use the Saved Objects API.
    """
    try:
        # Query Kibana Saved Objects API for index-pattern or data-view containing "frontend"
        res = requests.get(
            "http://kibana:5601/api/saved_objects/_find?type=index-pattern&search_fields=title&search=*frontend*",
            headers={"kbn-xsrf": "true"},
            auth=ES_AUTH
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("total", 0) > 0:
                print("Stage 3 Validated: Data View created successfully.")
                return True
                
        # Also check type=data-view just in case Kibana versions refer to it differently
        res2 = requests.get(
            "http://kibana:5601/api/saved_objects/_find?type=data-view&search_fields=title&search=*frontend*",
            headers={"kbn-xsrf": "true"},
            auth=ES_AUTH
        )
        if res2.status_code == 200:
            data = res2.json()
            if data.get("total", 0) > 0:
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

def trigger_scenario_5_unassigned_shards():
    """
    Stage 5: Unassigned Shards (Allocation disabled)
    We create an index and disable allocation for it to simulate unassigned shards after a failure.
    """
    index_name = "network-logs-2026.01"
    headers = {"Content-Type": "application/json"}
    payload = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "routing.allocation.enable": "none"  # Force unassigned
            }
        }
    }
    try:
        # Ignore 400 if it already exists
        res = requests.put(f"{ES_HOST}/{index_name}", json=payload, auth=ES_AUTH)
        if res.status_code in [200, 201]:
            print("Successfully triggered Stage 5 (Unassigned shards).")
    except Exception as e:
        print(f"Failed to trigger Stage 5: {e}")

def trigger_scenario_6_mapping_explosion():
    """
    Stage 6: Mapping Explosion (Limit Exceeded)
    We create an index with a very low field limit.
    """
    index_name = "app-metrics-2026.01"
    payload = {
        "settings": {
            "index": {
                "mapping.total_fields.limit": 2
            }
        },
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "message": {"type": "text"}
            }
        }
    }
    try:
        requests.put(f"{ES_HOST}/{index_name}", json=payload, auth=ES_AUTH)
        print("Successfully triggered Stage 6 (Mapping Limit).")
    except Exception as e:
        print(f"Failed to trigger Stage 6: {e}")

def validate_stage_5():
    """
    Validates Stage 5: Checks if the user enabled routing allocation for network-logs.
    """
    try:
        res = requests.get(f"{ES_HOST}/network-logs-2026.01/_settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            allocation = settings.get("network-logs-2026.01", {}).get("settings", {}).get("index", {}).get("routing", {}).get("allocation", {}).get("enable")
            
            # If default (omitted) or explicitly 'all'
            if not allocation or allocation == "all":
                print("Stage 5 Validated: Allocation enabled.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_6():
    """
    Validates Stage 6: Checks if the mapping limit is increased.
    """
    try:
        res = requests.get(f"{ES_HOST}/app-metrics-2026.01/_settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            limit = settings.get("app-metrics-2026.01", {}).get("settings", {}).get("index", {}).get("mapping", {}).get("total_fields", {}).get("limit")
            
            # Default is higher, or they increased it to > 2. Even if it's implicitly removed, `limit` will be None.
            if not limit or int(limit) > 2:
                print("Stage 6 Validated: Mapping limit increased.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def trigger_scenario_7_circuit_breaker():
    """
    Stage 7: JVM Circuit Breaker (Memory Pressure)
    We set the fielddata limit incredibly low so queries fail with 429 Too Many Requests.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "persistent": {
            "indices.breaker.fielddata.limit": "1kb"
        }
    }
    try:
        res = requests.put(f"{ES_HOST}/_cluster/settings", json=payload, auth=ES_AUTH)
        if res.status_code == 200:
            print("Successfully triggered Stage 7 (Circuit Breaker limit).")
    except Exception as e:
        print(f"Failed to trigger Stage 7: {e}")

def trigger_scenario_8_slow_tasks():
    """
    Stage 8: Heavy Search Load / Slow Tasks
    We launch a background reindex task that is deliberately throttled to take forever.
    The user must cancel the task using the Tasks API.
    """
    payload = {
        "source": {"index": "logstash-*"},
        "dest": {"index": "slow-reindex-dummy"}
    }
    try:
        # requests_per_second=0.1 means it processes at most 1 document every 10 seconds.
        # wait_for_completion=false sends the task to the background.
        res = requests.post(f"{ES_HOST}/_reindex?wait_for_completion=false&requests_per_second=0.1", json=payload, auth=ES_AUTH)
        if res.status_code == 200:
            print("Successfully triggered Stage 8 (Slow reindex task).")
    except Exception as e:
        print(f"Failed to trigger Stage 8: {e}")

def validate_stage_7():
    """
    Validates Stage 7: Checks if the user reset the circuit breaker limit.
    """
    try:
        res = requests.get(f"{ES_HOST}/_cluster/settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            limit = settings.get("persistent", {}).get("indices", {}).get("breaker", {}).get("fielddata", {}).get("limit")
            
            # If default (omitted) or not 1kb
            if not limit or limit != "1kb":
                print("Stage 7 Validated: Circuit breaker limit fixed.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_8():
    """
    Validates Stage 8: Checks if the user cancelled the slow reindex task.
    """
    try:
        res = requests.get(f"{ES_HOST}/_tasks?actions=*reindex", auth=ES_AUTH)
        if res.status_code == 200:
            data = res.json()
            nodes = data.get("nodes", {})
            tasks_found = False
            for node_id, node_info in nodes.items():
                if len(node_info.get("tasks", {})) > 0:
                    tasks_found = True
                    break
            
            if not tasks_found:
                print("Stage 8 Validated: Reindex task cancelled successfully.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def trigger_scenario_9_ilm_error():
    """
    Stage 9: ILM (Index Lifecycle Management) Failure
    We create two indices with the same alias but neither is marked as the write_index.
    Writes to the alias will fail.
    """
    try:
        # Create first index
        requests.put(f"{ES_HOST}/app-logs-000001", auth=ES_AUTH)
        # Create second index
        requests.put(f"{ES_HOST}/app-logs-000002", auth=ES_AUTH)
        
        # Add alias to both without is_write_index
        alias_payload = {
            "actions": [
                {"add": {"index": "app-logs-000001", "alias": "app-logs"}},
                {"add": {"index": "app-logs-000002", "alias": "app-logs"}}
            ]
        }
        res = requests.post(f"{ES_HOST}/_aliases", json=alias_payload, auth=ES_AUTH)
        if res.status_code == 200:
            print("Successfully triggered Stage 9 (ILM Alias Write Index missing).")
    except Exception as e:
        print(f"Failed to trigger Stage 9: {e}")

def trigger_scenario_10_mapping_conflict():
    """
    Stage 10: Mapping Conflict / Type Mismatch
    We create an index with a 'long' mapped payment_id.
    """
    payload = {
        "mappings": {
            "properties": {
                "payment_id": {"type": "long"},
                "amount": {"type": "float"}
            }
        }
    }
    try:
        res = requests.put(f"{ES_HOST}/orders-2026.01", json=payload, auth=ES_AUTH)
        if res.status_code in [200, 201]:
            print("Successfully triggered Stage 10 (Mapping strict conflict).")
    except Exception as e:
        print(f"Failed to trigger Stage 10: {e}")

def validate_stage_9():
    """
    Validates Stage 9: Checks if the user designated a write_index for the app-logs alias.
    """
    try:
        res = requests.get(f"{ES_HOST}/_alias/app-logs", auth=ES_AUTH)
        if res.status_code == 200:
            data = res.json()
            # data dict looks like: { "app-logs-000001": { "aliases": { "app-logs": { "is_write_index": true } } } }
            for index_name, index_info in data.items():
                alias_info = index_info.get("aliases", {}).get("app-logs", {})
                if alias_info.get("is_write_index") is True:
                    print("Stage 9 Validated: Write index assigned correctly.")
                    return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_10():
    """
    Validates Stage 10: Checks if any orders-2026.* index now has payment_id mapped to keyword.
    """
    try:
        res = requests.get(f"{ES_HOST}/orders-*/_mapping", auth=ES_AUTH)
        if res.status_code == 200:
            data = res.json()
            for index_name, index_info in data.items():
                mapping_type = index_info.get("mappings", {}).get("properties", {}).get("payment_id", {}).get("type")
                if mapping_type == "keyword":
                    print("Stage 10 Validated: Mapping type fixed to keyword.")
                    return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def trigger_scenario_11_snapshot_repo():
    """
    Stage 11: Snapshot Repository setup
    We do not change state here, we simply require the user to configure an `fs` snapshot repo.
    """
    print("Successfully triggered Stage 11 (Snapshot repository request).")
    
def trigger_scenario_12_oversharding():
    """
    Stage 12: Over-sharding limits
    We artificially restrict cluster.max_shards_per_node to 1.
    """
    payload = {
        "persistent": {
            "cluster.max_shards_per_node": 1
        }
    }
    try:
        res = requests.put(f"{ES_HOST}/_cluster/settings", json=payload, auth=ES_AUTH)
        if res.status_code == 200:
            print("Successfully triggered Stage 12 (Over-sharding limit).")
    except Exception as e:
        print(f"Failed to trigger Stage 12: {e}")

def validate_stage_11():
    """
    Validates Stage 11: Checks if any snapshot repository is configured.
    """
    try:
        res = requests.get(f"{ES_HOST}/_snapshot/_all", auth=ES_AUTH)
        if res.status_code == 200:
            repos = res.json()
            if len(repos) > 0:
                print("Stage 11 Validated: Snapshot repository configured.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_12():
    """
    Validates Stage 12: Checks if cluster.max_shards_per_node is restored.
    """
    try:
        res = requests.get(f"{ES_HOST}/_cluster/settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            limit = settings.get("persistent", {}).get("cluster", {}).get("max_shards_per_node")
            
            # Default is mostly missing / 1000, or something > 1
            if limit is None or int(limit) > 1:
                print("Stage 12 Validated: Shard limits increased.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def trigger_scenario_13_destructive_actions():
    """
    Stage 13: Destructive Actions Blocked
    We restrict using wildcards for destructive actions like delete indices.
    """
    payload = {
        "persistent": {
            "action.destructive_requires_name": True
        }
    }
    try:
        res = requests.put(f"{ES_HOST}/_cluster/settings", json=payload, auth=ES_AUTH)
        if res.status_code == 200:
            print("Successfully triggered Stage 13 (Destructive Actions).")
    except Exception as e:
        print(f"Failed to trigger Stage 13: {e}")

def trigger_scenario_14_max_result_window():
    """
    Stage 14: Deep Pagination / Max Result Window
    We create an index with a very low max_result_window (100) causing queries to fail if deep paginated.
    """
    index_name = "customers-2026.01"
    payload = {
        "settings": {
            "index": {
                "max_result_window": 100
            }
        }
    }
    try:
        requests.put(f"{ES_HOST}/{index_name}", json=payload, auth=ES_AUTH)
        requests.post(f"{ES_HOST}/{index_name}/_doc", json={"name": "test"}, auth=ES_AUTH)
        print("Successfully triggered Stage 14 (Max result window).")
    except Exception as e:
        print(f"Failed to trigger Stage 14: {e}")

def trigger_scenario_15_allocation_awareness():
    """
    Stage 15: Allocation Awareness
    We create an index that demands 'cold' hardware which doesn't exist.
    """
    index_name = "archive-logs-2026"
    payload = {
        "settings": {
            "index": {
                "routing.allocation.require.box_type": "cold"
            }
        }
    }
    try:
        requests.put(f"{ES_HOST}/{index_name}", json=payload, auth=ES_AUTH)
        print("Successfully triggered Stage 15 (Allocation Awareness).")
    except Exception as e:
        print(f"Failed to trigger Stage 15: {e}")

def validate_stage_13():
    """
    Validates Stage 13: Checks if destructive actions require name is false.
    """
    try:
        res = requests.get(f"{ES_HOST}/_cluster/settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            val = settings.get("persistent", {}).get("action", {}).get("destructive_requires_name")
            if val is False or str(val).lower() == "false":
                print("Stage 13 Validated: Destructive actions allowed.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_14():
    """
    Validates Stage 14: Checks if max result window is increased.
    """
    try:
        res = requests.get(f"{ES_HOST}/customers-2026.01/_settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            limit = settings.get("customers-2026.01", {}).get("settings", {}).get("index", {}).get("max_result_window")
            if not limit or int(limit) > 100:
                print("Stage 14 Validated: Max result window increased.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False

def validate_stage_15():
    """
    Validates Stage 15: Checks if allocation awareness requirement is fixed.
    """
    try:
        res = requests.get(f"{ES_HOST}/archive-logs-2026/_settings", auth=ES_AUTH)
        if res.status_code == 200:
            settings = res.json()
            box_type = settings.get("archive-logs-2026", {}).get("settings", {}).get("index", {}).get("routing", {}).get("allocation", {}).get("require", {}).get("box_type")
            if not box_type or box_type != "cold":
                print("Stage 15 Validated: Allocation awareness fixed.")
                return True
    except Exception as e:
        print(f"Validation error: {e}")
    return False
