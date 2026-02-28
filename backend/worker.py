import time
import json
import socket
import random
from faker import Faker
from elasticsearch import Elasticsearch
from app.database import SessionLocal
from app.models import Player, Scenario
from app.config import settings

fake = Faker()

ES_HOST = settings.es_host
LOGSTASH_HOST = settings.logstash_host
LOGSTASH_PORT = settings.logstash_port

es = Elasticsearch(
    [ES_HOST],
    basic_auth=(settings.es_user, settings.es_password),
    verify_certs=settings.es_verify_certs
)

def send_to_logstash(log_record: dict):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((LOGSTASH_HOST, LOGSTASH_PORT))
        s.sendall((json.dumps(log_record) + "\n").encode("utf-8"))
        s.close()
    except Exception as e:
        print(f"Failed to send to logstash: {e}")

def generate_web_log():
    """Generates standard web access logs directly into ES"""
    doc = {
        "timestamp": time.time(),
        "ip": fake.ipv4(),
        "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
        "url": fake.uri_path(),
        "status_code": random.choice([200, 201, 400, 401, 403, 404, 500, 503]),
        "user_agent": fake.user_agent()
    }
    try:
        es.index(index=f"weblogs-{time.strftime('%Y.%m.%d')}", document=doc)
    except Exception as e:
        print(f"ES indexing error: {e}")

def generate_billing_log(is_broken=False):
    """Sends via Logstash to simulate grok failures in the first scenario."""
    # INTENTIONAL BUG mode: if 'is_broken' is true, we send logs that fail the grok parse
    level = random.choice(["INFO", "WARN", "ERROR"])
    msg = fake.sentence()
    
    if is_broken:
        # Does NOT match: %{IP:client} - %{GREEDYDATA:msg}
        # Instead of 'IP - MSG', we do 'MSG IP' or something weird
        raw_message = f"{msg} [from {fake.ipv4()}]"
    else:
        # Correct grok format
        raw_message = f"{fake.ipv4()} - {msg}"
    
    log_record = {
        "log_type": "billing_service",
        "message": raw_message,
        "level": level
    }
    send_to_logstash(log_record)

def run_worker():
    print("Starting Elastic Simulator Log Generator Worker...")
    print("🔥 DATABASE_URL USED =")
    print(os.getenv("DATABASE_URL"))
    
    while True:
        
        # Connect to DB to check active scenario state based on users
        # For simplicity in this demo worker, we just see if ANY player is on Stage 1
        db = SessionLocal()
        players = db.query(Player).all()
        
        has_player_stage_1 = any(p.current_stage == 1 for p in players)
        # If no players, we still generate some healthy logs
        is_stage_1_active = has_player_stage_1 or len(players) == 0

        # Generate 5 web logs
        for _ in range(5):
            generate_web_log()
        
        # Generate 2 billing logs (Broken if Stage 1 is active, normal otherwise)
        for _ in range(2):
            generate_billing_log(is_broken=is_stage_1_active)

        db.close()
        time.sleep(2) # Run every 2 seconds

if __name__ == "__main__":
    run_worker()
