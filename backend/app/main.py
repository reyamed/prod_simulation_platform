from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import uvicorn
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jose import JWTError

from . import models, schemas
from .database import engine, get_db
from .auth import verify_password, get_password_hash, create_access_token
from .config import settings

# Create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Elastic Simulator API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Elastic Simulator Engine"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.Player).filter(models.Player.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/register", response_model=schemas.Player)
def register(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    db_email = db.query(models.Player).filter(models.Player.email == player.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    db_username = db.query(models.Player).filter(models.Player.username == player.username).first()
    if db_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = get_password_hash(player.password)
    new_player = models.Player(
        username=player.username, 
        email=player.email,
        hashed_password=hashed_password
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Player).filter(models.Player.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.Player)
def read_users_me(current_user: models.Player = Depends(get_current_user)):
    return current_user

@app.get("/tickets", response_model=list[schemas.Ticket])
def read_player_tickets(current_user: models.Player = Depends(get_current_user), db: Session = Depends(get_db)):
    tickets = db.query(models.Ticket).filter(models.Ticket.player_id == current_user.id).order_by(models.Ticket.id.desc()).all()
    return tickets

@app.get("/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    total_players = db.query(models.Player).count()
    stage_breakdown = db.query(models.Player.current_stage, func.count(models.Player.id)).group_by(models.Player.current_stage).all()
    top_players = db.query(models.Player).order_by(models.Player.score.desc()).limit(10).all()
    
    return {
        "total_players": total_players,
        "stage_breakdown": [{"stage": s, "count": c} for s, c in stage_breakdown],
        "top_players": [{"username": p.username, "score": p.score, "stage": p.current_stage} for p in top_players]
    }

from .orchestrator import validate_stage_1, validate_stage_2, validate_stage_3, validate_stage_4, validate_stage_5, validate_stage_6, validate_stage_7, validate_stage_8, validate_stage_9, validate_stage_10, validate_stage_11, validate_stage_12, validate_stage_13, validate_stage_14, validate_stage_15, trigger_scenario_2_replicas, trigger_scenario_3_data_view, trigger_scenario_4_hard_disk_watermark, trigger_scenario_5_unassigned_shards, trigger_scenario_6_mapping_explosion, trigger_scenario_7_circuit_breaker, trigger_scenario_8_slow_tasks, trigger_scenario_9_ilm_error, trigger_scenario_10_mapping_conflict, trigger_scenario_11_snapshot_repo, trigger_scenario_12_oversharding, trigger_scenario_13_destructive_actions, trigger_scenario_14_max_result_window, trigger_scenario_15_allocation_awareness

@app.post("/game/start")
def start_game(current_user: models.Player = Depends(get_current_user), db: Session = Depends(get_db)):
    scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 1).first()
    if not scenario:
        scenario = models.Scenario(
            title="Missing Billing Logs",
            description="Fix the Grok parse failure in Logstash.",
            difficulty=models.ScenarioDifficulty.EASY,
            stage_order=1,
            validation_type="check_grok",
            hints='["Check the Logstash container logs for grokparsefailures.", "Compare the python worker format in worker.py to logstash.conf grok patterns.", "[Grok Documentation](https://www.elastic.co/guide/en/logstash/current/plugins-filters-grok.html)"]'
        )
        db.add(scenario)
        db.commit()
        
    ticket = db.query(models.Ticket).filter(models.Ticket.player_id == current_user.id, models.Ticket.scenario_id == scenario.id).first()
    if not ticket:
        ticket = models.Ticket(
            scenario_id=scenario.id,
            player_id=current_user.id,
            sender_name="DevOps Dave",
            subject="Billing logs are missing!",
            body="Hey! My billing service logs are not showing up in Kibana since deploy! Please fix immediately.",
            status=models.TicketStatus.OPEN,
            hints=scenario.hints
        )
        db.add(ticket)
        db.commit()

    return {"player_id": current_user.id}

@app.post("/game/validate")
def validate_game(request: schemas.TicketValidationRequest, current_user: models.Player = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == request.ticket_id,
        models.Ticket.player_id == current_user.id
    ).first()

    if not ticket:
        return {"success": False, "message": "Ticket not found or doesn't belong to you."}
        
    if ticket.status == models.TicketStatus.RESOLVED:
        return {"success": False, "message": "Ticket is already resolved."}

    scenario_stage = ticket.scenario.stage_order

    if scenario_stage == 1:
        is_valid = validate_stage_1()
        if is_valid:
            if current_user.current_stage == 1:
                current_user.current_stage = 2
            current_user.score += 100
            
            ticket.status = models.TicketStatus.RESOLVED

            # Generate Stage 2 Scenario and Ticket
            trigger_scenario_2_replicas()
            scenario2 = db.query(models.Scenario).filter(models.Scenario.stage_order == 2).first()
            if not scenario2:
                scenario2 = models.Scenario(
                    title="Cluster Yellow (Indices & Replicas)",
                    description="Fix the unassigned replica shard causing yellow cluster health.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=2,
                    validation_type="check_cluster_health",
                    hints='["Open Kibana and go to Stack Management -> Index Management.", "Look at `transactions-2026.01`.", "Since we only have 1 node, a replica cannot be assigned to a different host.", "Use Kibana Dev Tools to update `index.routing.allocation.total_shards_per_node: 2` for this index, or set replicas to 0 if you prefer.", "[Index Allocation Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/allocation-total-shards.html)"]'
                )
                db.add(scenario2)
                db.commit()
            
            ticket2 = models.Ticket(
                scenario_id=scenario2.id,
                player_id=current_user.id,
                sender_name="Tech Lead",
                subject="Cluster Health is Yellow - Unassigned Shards!",
                body="I just noticed our development cluster is in a Yellow state. Can you check Kibana and fix the unassigned replica shards for the new transactions index? Don\'t just delete the replicas, try allowing multiple shards on our single node.",
                status=models.TicketStatus.OPEN,
                hints=scenario2.hints
            )
            db.add(ticket2)
            db.commit()
            return {"success": True, "message": "Stage 1 validated! Welcome to Stage 2."}
        else:
            return {"success": False, "message": "Validation failed. Check the grok patterns in Elastic/Logstash."}
            
    if scenario_stage == 2:
        is_valid = validate_stage_2()
        if is_valid:
            if current_user.current_stage == 2:
                current_user.current_stage = 3
            current_user.score += 150
            
            ticket.status = models.TicketStatus.RESOLVED

            # Generate Stage 3 Scenario and Ticket
            trigger_scenario_3_data_view()
            scenario3 = db.query(models.Scenario).filter(models.Scenario.stage_order == 3).first()
            if not scenario3:
                scenario3 = models.Scenario(
                    title="Missing Kibana Data View",
                    description="Create a data view in Kibana to allow developers to search log data.",
                    difficulty=models.ScenarioDifficulty.EASY,
                    stage_order=3,
                    validation_type="check_kibana_data_view",
                    hints='["Go to Kibana -> Stack Management -> Data Views.", "Click \'Create data view\'.", "Use `frontend-logs-*` as the Index pattern.", "Select `@timestamp` as the time field.", "[Data Views Documentation](https://www.elastic.co/guide/en/kibana/current/data-views.html)"]'
                )
                db.add(scenario3)
                db.commit()
            
            ticket3 = models.Ticket(
                scenario_id=scenario3.id,
                player_id=current_user.id,
                sender_name="Frontend Dev Team",
                subject="Can't find our logs in Kibana!",
                body="We deployed the new UI, and supposedly logs are streaming to Elasticsearch... but when I go to Kibana Discover I can't look them up? Help us out!",
                status=models.TicketStatus.OPEN,
                hints=scenario3.hints
            )
            db.add(ticket3)
            db.commit()
            return {"success": True, "message": "Stage 2 validated! Welcome to Stage 3."}
        else:
            return {"success": False, "message": "Validation failed. The transactions index replica is still unassigned or misconfigured."}

    if scenario_stage == 3:
        is_valid = validate_stage_3()
        if is_valid:
            if current_user.current_stage == 3:
                current_user.current_stage = 4
            current_user.score += 200
            
            ticket.status = models.TicketStatus.RESOLVED

            # Generate Stage 4 Scenario and Ticket
            trigger_scenario_4_hard_disk_watermark()
            scenario4 = db.query(models.Scenario).filter(models.Scenario.stage_order == 4).first()
            if not scenario4:
                scenario4 = models.Scenario(
                    title="Read-Only Cluster Blocks",
                    description="Clear the flood-stage disk watermark cluster blocks.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=4,
                    validation_type="check_cluster_routing",
                    hints='["All indices are rejecting writes right now. This happens via `cluster.routing.allocation.disk.watermark.flood_stage`.", "Use Kibana Dev tools to check `GET /_cluster/settings`.", "Reset the watermark by setting it to `null`.", "`PUT /_cluster/settings { \\"persistent\\": { \\"cluster.routing.allocation.disk.watermark.flood_stage\\": null } }`", "[Disk Watermarks Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/modules-cluster.html#disk-based-shard-allocation)"]'
                )
                db.add(scenario4)
                db.commit()
            
            ticket4 = models.Ticket(
                scenario_id=scenario4.id,
                player_id=current_user.id,
                sender_name="Tech Lead",
                subject="CRITICAL: Logstash writes rejected (403)",
                body="Alert! We are dropping logs! Logstash is throwing 403 Forbidden index read-only errors. It looks like the cluster hit a disk watermark flood stage and locked itself down. We cleared up some space, but the blocks are still there. Can you clear the watermark blocks in Kibana so writes can resume?",
                status=models.TicketStatus.OPEN,
                hints=scenario4.hints
            )
            db.add(ticket4)
            db.commit()
            return {"success": True, "message": "Stage 3 validated! Welcome to Stage 4 (Final Boss)."}
        else:
            return {"success": False, "message": "Validation failed. Could not find a Data View matching 'frontend-logs-*'."}
            
    if scenario_stage == 4:
        is_valid = validate_stage_4()
        if is_valid:
            if current_user.current_stage == 4:
                current_user.current_stage = 5
            current_user.score += 250
            
            ticket.status = models.TicketStatus.RESOLVED

            # Generate Stage 5 Scenario and Ticket
            trigger_scenario_5_unassigned_shards()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 5).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Network Partition Shard Drop",
                    description="Fix the unassigned shards caused by a network partition.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=5,
                    validation_type="check_allocation",
                    hints='["Looks like allocation was disabled. Check `GET /network-logs-2026.01/_settings`.", "Set `index.routing.allocation.enable` back to `all` to let shards recover.", "`PUT /network-logs-2026.01/_settings { \\"index.routing.allocation.enable\\": \\"all\\" }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Infra Monitor",
                subject="Alert: Cluster Health Red - Unassigned Shards",
                body="We just had a brief network hiccup and lost contact with a node in the new `network-logs-2026.01` index. Allocation got turned off manually by our automation script to protect write availability. Please fix the allocation setting to recover the shards.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 4 validated! Welcome to Stage 5."}
        else:
            return {"success": False, "message": "Validation failed. The disk watermark flood stage blocks are still active."}
            
    if scenario_stage == 5:
        is_valid = validate_stage_5()
        if is_valid:
            if current_user.current_stage == 5:
                current_user.current_stage = 6
            current_user.score += 300
            
            ticket.status = models.TicketStatus.RESOLVED

            # Generate Stage 6
            trigger_scenario_6_mapping_explosion()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 6).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Mapping Limit Explosion",
                    description="Fix log indexing by raising the mapping fields limit.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=6,
                    validation_type="check_mapping_limit",
                    hints='["Elasticsearch has a safety limit on dynamic fields per index to prevent memory exhaustion.", "Increase `index.mapping.total_fields.limit` to something larger than 2.", "`PUT /app-metrics-2026.01/_settings { \\"index.mapping.total_fields.limit\\": 1000 }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="App Team Alpha",
                subject="400 Bad Request on Logstash?",
                body="Hey, our application `app-metrics-2026.01` is throwing max fields limit exceeded. I think someone set it to 2 by mistake? Can you raise the max mapping fields limit so we can ingest our JSON?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 5 validated! Welcome to Stage 6."}
        else:
            return {"success": False, "message": "Validation failed. The routing allocation is still disabled."}

    if scenario_stage == 6:
        is_valid = validate_stage_6()
        if is_valid:
            if current_user.current_stage == 6:
                current_user.current_stage = 7
            current_user.score += 300
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_7_circuit_breaker()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 7).first()
            if not scenario:
                scenario = models.Scenario(
                    title="JVM Circuit Breaker",
                    description="Clear the fielddata memory limit to restore query capabilities.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=7,
                    validation_type="check_circuit_breaker",
                    hints='["Queries are failing with 429 Too Many Requests because the `indices.breaker.fielddata.limit` was set dangerously low.", "Use Kibana Dev tools to reset it.", "`PUT /_cluster/settings { \\"persistent\\": { \\"indices.breaker.fielddata.limit\\": null } }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="BI Analytics Team",
                subject="Kibana Dashboards are throwing 429 errors!",
                body="We tried running a huge aggregation and it seems we broke the cluster memory limits. Now every query throws a circuit breaker exception. Can you reset the fielddata breaker limit?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 6 validated! Welcome to Stage 7."}
        else:
            return {"success": False, "message": "Validation failed. The mapping limit is still 2 or less."}

    if scenario_stage == 7:
        is_valid = validate_stage_7()
        if is_valid:
            if current_user.current_stage == 7:
                current_user.current_stage = 8
            current_user.score += 400
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_8_slow_tasks()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 8).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Runaway Tasks",
                    description="Cancel the slow background task killing cluster performance.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=8,
                    validation_type="check_tasks_cancelled",
                    hints='["A throttled reindex task is holding resources.", "Use the Tasks API to find it: `GET /_tasks?detailed=true&actions=*reindex`.", "Copy the task_id (e.g. `node_id:12345`) and cancel it.", "`POST /_tasks/<task_id>/_cancel`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Data Engineering",
                subject="Accidental 1-doc-per-minute Reindex",
                body="I accidentally kicked off a background reindex from the billing logs, but I set the throttle to 1 request per 10 seconds. The cluster is dragging. Can you kill my task using the Task Management API?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 7 validated! Welcome to Stage 8."}
        else:
            return {"success": False, "message": "Validation failed. The circuit breaker limit is still tightly constrained."}

    if scenario_stage == 8:
        is_valid = validate_stage_8()
        if is_valid:
            if current_user.current_stage == 8:
                current_user.current_stage = 9
            current_user.score += 350
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_9_ilm_error()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 9).first()
            if not scenario:
                scenario = models.Scenario(
                    title="ILM Rollover Failure",
                    description="Fix the alias so that Index Lifecycle Management can roll over the index.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=9,
                    validation_type="check_ilm_alias",
                    hints='["For ILM to work, the alias must point to one and only one index with `is_write_index: true`.", "Use the POST `/_aliases` API to update the `app-logs` alias on index `app-logs-000002` setting `is_write_index` to true.", "`POST /_aliases { \\"actions\\": [ { \\"add\\": { \\"index\\": \\"app-logs-000002\\", \\"alias\\": \\"app-logs\\", \\"is_write_index\\": true } } ] }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Logistics System",
                subject="Indices won't roll over!",
                body="We set up ILM to roll over the `app-logs` indices, but it's throwing an illegal_argument exception saying 'no write index is defined for alias'. Can you fix the alias configuration?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 8 validated! Welcome to Stage 9."}
        else:
            return {"success": False, "message": "Validation failed. The rogue reindex task is still running."}

    if scenario_stage == 9:
        is_valid = validate_stage_9()
        if is_valid:
            if current_user.current_stage == 9:
                current_user.current_stage = 10
            current_user.score += 350
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_10_mapping_conflict()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 10).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Mapping Type Conflict",
                    description="Fix the explicit mapping so the UUID string can be ingested into a new index.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=10,
                    validation_type="check_mapping_type",
                    hints='["The field `payment_id` was mapped as a long, but the application is sending a string UUID.", "You cannot change an existing mapping.", "Create a new index like `orders-2026.02` with an explicit mapping defining `payment_id` as `keyword`.", "The validation will pass if any `orders-*` index has `payment_id` mapped to `keyword`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Backend Monolith",
                subject="Mapping parsing exception on orders!",
                body="We just deployed to production, and our new UUID format for `payment_id` is crashing against `orders-2026.01` because it expects a long integer. We are losing order data! Please fix the mapping by creating a new index like `orders-2026.02` that accepts a keyword type for `payment_id`.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 9 validated! Welcome to Stage 10."}
        else:
            return {"success": False, "message": "Validation failed. The app-logs alias does not have a designated write index."}

    if scenario_stage == 10:
        is_valid = validate_stage_10()
        if is_valid:
            if current_user.current_stage == 10:
                current_user.current_stage = 11
            current_user.score += 450
            
            ticket.status = models.TicketStatus.RESOLVED
                
            trigger_scenario_11_snapshot_repo()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 11).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Snapshot Repository Registration",
                    description="Configure an fs snapshot repository to enable automated backups.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=11,
                    validation_type="check_snapshot_repo",
                    hints='["Backups are failing because no repository is registered.", "Use `PUT /_snapshot/my_backup` with `type: fs` and `settings.location: /usr/share/elasticsearch/backups`.", "Warning: Elasticsearch requires `path.repo` to be set in `elasticsearch.yml` or as a container environment variable before you can register an `fs` repository! You might need to edit `docker-compose.yml` to inject `path.repo=/usr/share/elasticsearch/backups` and recreate the container!", "`PUT /_snapshot/my_backup { \\"type\\": \\"fs\\", \\"settings\\": { \\"location\\": \\"/usr/share/elasticsearch/backups\\" } }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Compliance Officer",
                subject="Missing Automated Backups",
                body="We failed our latest audit because the production cluster isn't running daily snapshots! We need a snapshot repository set up immediately. Please create an `fs` type repository named `my_backup` pointing to `/usr/share/elasticsearch/backups` down in the filesystem.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 10 validated! Welcome to Stage 11."}
        else:
            return {"success": False, "message": "Validation failed. No orders-* index has payment_id mapped to keyword."}

    if scenario_stage == 11:
        is_valid = validate_stage_11()
        if is_valid:
            if current_user.current_stage == 11:
                current_user.current_stage = 12
            current_user.score += 500
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_12_oversharding()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 12).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Scale Limit: Over-sharding",
                    description="Increase the cluster max_shards_per_node limit.",
                    difficulty=models.ScenarioDifficulty.EASY,
                    stage_order=12,
                    validation_type="check_cluster_shards",
                    hints='["The cluster refuses to create new indices because we hit the `cluster.max_shards_per_node` limit (which I restricted to 1 for this scenario).", "Use Kibana Dev tools to increase it back.", "`PUT /_cluster/settings { \\"persistent\\": { \\"cluster.max_shards_per_node\\": 1000 } }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Logstash Pipeline",
                subject="Validation Failed: this action would add [1] shards",
                body="Alert! We can't create today's daily log indices! Elasticsearch throws `Validation Failed: 1: this action would add [1] shards, but this cluster currently has [X]/[1] maximum normal shards in the cluster`. Please raise the global shards limit!",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 11 validated! Welcome to Stage 12."}
        else:
            return {"success": False, "message": "Validation failed. No snapshot repository is configured."}

    if scenario_stage == 12:
        is_valid = validate_stage_12()
        if is_valid:
            if current_user.current_stage == 12:
                current_user.current_stage = 13
            current_user.score += 200
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_13_destructive_actions()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 13).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Destructive Actions Blocked",
                    description="Allow destructive actions to be performed with wildcards again.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=13,
                    validation_type="check_destructive",
                    hints='["It seems `action.destructive_requires_name` is set to `true`.", "Use `PUT /_cluster/settings` to set it to `false`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="SRE Team",
                subject="Cronjobs failing: Destructive requires name",
                body="Hey, our nightly index cleanup cronjob is failing. It tries to delete `old-logs-*` but Elasticsearch throws an error saying destructive actions require a name. Can you lift this cluster-level restriction?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 12 validated! Welcome to Stage 13."}
        else:
            return {"success": False, "message": "Validation failed. Shard limits are still restricted."}

    if scenario_stage == 13:
        is_valid = validate_stage_13()
        if is_valid:
            if current_user.current_stage == 13:
                current_user.current_stage = 14
            current_user.score += 250
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_14_max_result_window()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 14).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Deep Pagination Failure",
                    description="Increase the max result window for the customers index.",
                    difficulty=models.ScenarioDifficulty.EASY,
                    stage_order=14,
                    validation_type="check_max_result",
                    hints='["Deep pagination failed because we requested an offset past the default limit.", "Increase `index.max_result_window` to something large like `10000` via `PUT /customers-2026.01/_settings`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Frontend Team",
                subject="Pagination broken on Customers page",
                body="When users go past page 10 on the customers list, the API returns a 500 error about Result Window. Someone must have accidentally lowered `max_result_window` to 100 on `customers-2026.01`. Please fix it.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 13 validated! Welcome to Stage 14."}
        else:
            return {"success": False, "message": "Validation failed. Destructive actions are still restricted."}

    if scenario_stage == 14:
        is_valid = validate_stage_14()
        if is_valid:
            if current_user.current_stage == 14:
                current_user.current_stage = 15
            current_user.score += 350
            
            ticket.status = models.TicketStatus.RESOLVED

            trigger_scenario_15_allocation_awareness()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 15).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Allocation Awareness Limits",
                    description="Remove the hardware restriction to allow the index to allocate.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=15,
                    validation_type="check_allocation_awareness",
                    hints='["The index requires a node with `data: cold` box type, but we only have 1 node.", "Use `PUT /archive-logs-2026/_settings` to set `index.routing.allocation.require.box_type` to `null`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="ILM Policy Engine",
                subject="Unassigned Shards on Archive Logs",
                body="The `archive-logs-2026` index is perpetually yellow/red. It looks like it's trying to allocate to a node with `box_type: cold`, but we don't have any cold nodes in this cluster right now! Please remove the routing requirement from the index settings.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage 14 validated! Welcome to Stage 15."}
        else:
            return {"success": False, "message": "Validation failed. Max result window is too small."}

    if scenario_stage == 15:
        is_valid = validate_stage_15()
        if is_valid:
            if current_user.current_stage == 15:
                current_user.current_stage = 16
            current_user.score += 1000
            
            ticket.status = models.TicketStatus.RESOLVED
                
            db.commit()
            return {"success": True, "message": "CONGRATULATIONS! You have fully completed the Advanced Elasticsearch Simulation Platform (15/15)!"}
        else:
            return {"success": False, "message": "Validation failed. The allocation requirement is still active."}

    return {"success": True, "message": "You have completed the available testing stages!"}

@app.post("/game/skip")
def skip_game_stage(request: schemas.TicketValidationRequest, current_user: models.Player = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == request.ticket_id,
        models.Ticket.player_id == current_user.id
    ).first()

    if not ticket:
        return {"success": False, "message": "Ticket not found or doesn't belong to you."}
        
    if ticket.status == models.TicketStatus.RESOLVED:
        return {"success": False, "message": "Ticket is already resolved."}

    scenario_stage = ticket.scenario.stage_order

    if scenario_stage == 1:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 1:
                current_user.current_stage = 2
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            # Generate Stage 2 Scenario and Ticket
            trigger_scenario_2_replicas()
            scenario2 = db.query(models.Scenario).filter(models.Scenario.stage_order == 2).first()
            if not scenario2:
                scenario2 = models.Scenario(
                    title="Cluster Yellow (Indices & Replicas)",
                    description="Fix the unassigned replica shard causing yellow cluster health.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=2,
                    validation_type="check_cluster_health",
                    hints='["Open Kibana and go to Stack Management -> Index Management.", "Look at `transactions-2026.01`.", "Since we only have 1 node, a replica cannot be assigned to a different host.", "Use Kibana Dev Tools to update `index.routing.allocation.total_shards_per_node: 2` for this index, or set replicas to 0 if you prefer.", "[Index Allocation Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/allocation-total-shards.html)"]'
                )
                db.add(scenario2)
                db.commit()
            
            ticket2 = models.Ticket(
                scenario_id=scenario2.id,
                player_id=current_user.id,
                sender_name="Tech Lead",
                subject="Cluster Health is Yellow - Unassigned Shards!",
                body="I just noticed our development cluster is in a Yellow state. Can you check Kibana and fix the unassigned replica shards for the new transactions index? Don\'t just delete the replicas, try allowing multiple shards on our single node.",
                status=models.TicketStatus.OPEN,
                hints=scenario2.hints
            )
            db.add(ticket2)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. Check the grok patterns in Elastic/Logstash."}
            
    if scenario_stage == 2:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 2:
                current_user.current_stage = 3
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            # Generate Stage 3 Scenario and Ticket
            trigger_scenario_3_data_view()
            scenario3 = db.query(models.Scenario).filter(models.Scenario.stage_order == 3).first()
            if not scenario3:
                scenario3 = models.Scenario(
                    title="Missing Kibana Data View",
                    description="Create a data view in Kibana to allow developers to search log data.",
                    difficulty=models.ScenarioDifficulty.EASY,
                    stage_order=3,
                    validation_type="check_kibana_data_view",
                    hints='["Go to Kibana -> Stack Management -> Data Views.", "Click \'Create data view\'.", "Use `frontend-logs-*` as the Index pattern.", "Select `@timestamp` as the time field.", "[Data Views Documentation](https://www.elastic.co/guide/en/kibana/current/data-views.html)"]'
                )
                db.add(scenario3)
                db.commit()
            
            ticket3 = models.Ticket(
                scenario_id=scenario3.id,
                player_id=current_user.id,
                sender_name="Frontend Dev Team",
                subject="Can't find our logs in Kibana!",
                body="We deployed the new UI, and supposedly logs are streaming to Elasticsearch... but when I go to Kibana Discover I can't look them up? Help us out!",
                status=models.TicketStatus.OPEN,
                hints=scenario3.hints
            )
            db.add(ticket3)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The transactions index replica is still unassigned or misconfigured."}

    if scenario_stage == 3:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 3:
                current_user.current_stage = 4
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            # Generate Stage 4 Scenario and Ticket
            trigger_scenario_4_hard_disk_watermark()
            scenario4 = db.query(models.Scenario).filter(models.Scenario.stage_order == 4).first()
            if not scenario4:
                scenario4 = models.Scenario(
                    title="Read-Only Cluster Blocks",
                    description="Clear the flood-stage disk watermark cluster blocks.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=4,
                    validation_type="check_cluster_routing",
                    hints='["All indices are rejecting writes right now. This happens via `cluster.routing.allocation.disk.watermark.flood_stage`.", "Use Kibana Dev tools to check `GET /_cluster/settings`.", "Reset the watermark by setting it to `null`.", "`PUT /_cluster/settings { \\"persistent\\": { \\"cluster.routing.allocation.disk.watermark.flood_stage\\": null } }`", "[Disk Watermarks Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/modules-cluster.html#disk-based-shard-allocation)"]'
                )
                db.add(scenario4)
                db.commit()
            
            ticket4 = models.Ticket(
                scenario_id=scenario4.id,
                player_id=current_user.id,
                sender_name="Tech Lead",
                subject="CRITICAL: Logstash writes rejected (403)",
                body="Alert! We are dropping logs! Logstash is throwing 403 Forbidden index read-only errors. It looks like the cluster hit a disk watermark flood stage and locked itself down. We cleared up some space, but the blocks are still there. Can you clear the watermark blocks in Kibana so writes can resume?",
                status=models.TicketStatus.OPEN,
                hints=scenario4.hints
            )
            db.add(ticket4)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. Could not find a Data View matching 'frontend-logs-*'."}
            
    if scenario_stage == 4:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 4:
                current_user.current_stage = 5
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            # Generate Stage 5 Scenario and Ticket
            trigger_scenario_5_unassigned_shards()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 5).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Network Partition Shard Drop",
                    description="Fix the unassigned shards caused by a network partition.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=5,
                    validation_type="check_allocation",
                    hints='["Looks like allocation was disabled. Check `GET /network-logs-2026.01/_settings`.", "Set `index.routing.allocation.enable` back to `all` to let shards recover.", "`PUT /network-logs-2026.01/_settings { \\"index.routing.allocation.enable\\": \\"all\\" }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Infra Monitor",
                subject="Alert: Cluster Health Red - Unassigned Shards",
                body="We just had a brief network hiccup and lost contact with a node in the new `network-logs-2026.01` index. Allocation got turned off manually by our automation script to protect write availability. Please fix the allocation setting to recover the shards.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The disk watermark flood stage blocks are still active."}
            
    if scenario_stage == 5:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 5:
                current_user.current_stage = 6
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            # Generate Stage 6
            trigger_scenario_6_mapping_explosion()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 6).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Mapping Limit Explosion",
                    description="Fix log indexing by raising the mapping fields limit.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=6,
                    validation_type="check_mapping_limit",
                    hints='["Elasticsearch has a safety limit on dynamic fields per index to prevent memory exhaustion.", "Increase `index.mapping.total_fields.limit` to something larger than 2.", "`PUT /app-metrics-2026.01/_settings { \\"index.mapping.total_fields.limit\\": 1000 }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="App Team Alpha",
                subject="400 Bad Request on Logstash?",
                body="Hey, our application `app-metrics-2026.01` is throwing max fields limit exceeded. I think someone set it to 2 by mistake? Can you raise the max mapping fields limit so we can ingest our JSON?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The routing allocation is still disabled."}

    if scenario_stage == 6:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 6:
                current_user.current_stage = 7
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_7_circuit_breaker()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 7).first()
            if not scenario:
                scenario = models.Scenario(
                    title="JVM Circuit Breaker",
                    description="Clear the fielddata memory limit to restore query capabilities.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=7,
                    validation_type="check_circuit_breaker",
                    hints='["Queries are failing with 429 Too Many Requests because the `indices.breaker.fielddata.limit` was set dangerously low.", "Use Kibana Dev tools to reset it.", "`PUT /_cluster/settings { \\"persistent\\": { \\"indices.breaker.fielddata.limit\\": null } }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="BI Analytics Team",
                subject="Kibana Dashboards are throwing 429 errors!",
                body="We tried running a huge aggregation and it seems we broke the cluster memory limits. Now every query throws a circuit breaker exception. Can you reset the fielddata breaker limit?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The mapping limit is still 2 or less."}

    if scenario_stage == 7:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 7:
                current_user.current_stage = 8
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_8_slow_tasks()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 8).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Runaway Tasks",
                    description="Cancel the slow background task killing cluster performance.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=8,
                    validation_type="check_tasks_cancelled",
                    hints='["A throttled reindex task is holding resources.", "Use the Tasks API to find it: `GET /_tasks?detailed=true&actions=*reindex`.", "Copy the task_id (e.g. `node_id:12345`) and cancel it.", "`POST /_tasks/<task_id>/_cancel`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Data Engineering",
                subject="Accidental 1-doc-per-minute Reindex",
                body="I accidentally kicked off a background reindex from the billing logs, but I set the throttle to 1 request per 10 seconds. The cluster is dragging. Can you kill my task using the Task Management API?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The circuit breaker limit is still tightly constrained."}

    if scenario_stage == 8:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 8:
                current_user.current_stage = 9
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_9_ilm_error()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 9).first()
            if not scenario:
                scenario = models.Scenario(
                    title="ILM Rollover Failure",
                    description="Fix the alias so that Index Lifecycle Management can roll over the index.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=9,
                    validation_type="check_ilm_alias",
                    hints='["For ILM to work, the alias must point to one and only one index with `is_write_index: true`.", "Use the POST `/_aliases` API to update the `app-logs` alias on index `app-logs-000002` setting `is_write_index` to true.", "`POST /_aliases { \\"actions\\": [ { \\"add\\": { \\"index\\": \\"app-logs-000002\\", \\"alias\\": \\"app-logs\\", \\"is_write_index\\": true } } ] }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Logistics System",
                subject="Indices won't roll over!",
                body="We set up ILM to roll over the `app-logs` indices, but it's throwing an illegal_argument exception saying 'no write index is defined for alias'. Can you fix the alias configuration?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The rogue reindex task is still running."}

    if scenario_stage == 9:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 9:
                current_user.current_stage = 10
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_10_mapping_conflict()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 10).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Mapping Type Conflict",
                    description="Fix the explicit mapping so the UUID string can be ingested into a new index.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=10,
                    validation_type="check_mapping_type",
                    hints='["The field `payment_id` was mapped as a long, but the application is sending a string UUID.", "You cannot change an existing mapping.", "Create a new index like `orders-2026.02` with an explicit mapping defining `payment_id` as `keyword`.", "The validation will pass if any `orders-*` index has `payment_id` mapped to `keyword`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Backend Monolith",
                subject="Mapping parsing exception on orders!",
                body="We just deployed to production, and our new UUID format for `payment_id` is crashing against `orders-2026.01` because it expects a long integer. We are losing order data! Please fix the mapping by creating a new index like `orders-2026.02` that accepts a keyword type for `payment_id`.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. The app-logs alias does not have a designated write index."}

    if scenario_stage == 10:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 10:
                current_user.current_stage = 11
            
            ticket.status = models.TicketStatus.IN_PROGRESS
                
            trigger_scenario_11_snapshot_repo()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 11).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Snapshot Repository Registration",
                    description="Configure an fs snapshot repository to enable automated backups.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=11,
                    validation_type="check_snapshot_repo",
                    hints='["Backups are failing because no repository is registered.", "Use `PUT /_snapshot/my_backup` with `type: fs` and `settings.location: /usr/share/elasticsearch/backups`.", "Warning: Elasticsearch requires `path.repo` to be set in `elasticsearch.yml` or as a container environment variable before you can register an `fs` repository! You might need to edit `docker-compose.yml` to inject `path.repo=/usr/share/elasticsearch/backups` and recreate the container!", "`PUT /_snapshot/my_backup { \\"type\\": \\"fs\\", \\"settings\\": { \\"location\\": \\"/usr/share/elasticsearch/backups\\" } }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Compliance Officer",
                subject="Missing Automated Backups",
                body="We failed our latest audit because the production cluster isn't running daily snapshots! We need a snapshot repository set up immediately. Please create an `fs` type repository named `my_backup` pointing to `/usr/share/elasticsearch/backups` down in the filesystem.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. No orders-* index has payment_id mapped to keyword."}

    if scenario_stage == 11:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 11:
                current_user.current_stage = 12
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_12_oversharding()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 12).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Scale Limit: Over-sharding",
                    description="Increase the cluster max_shards_per_node limit.",
                    difficulty=models.ScenarioDifficulty.EASY,
                    stage_order=12,
                    validation_type="check_cluster_shards",
                    hints='["The cluster refuses to create new indices because we hit the `cluster.max_shards_per_node` limit (which I restricted to 1 for this scenario).", "Use Kibana Dev tools to increase it back.", "`PUT /_cluster/settings { \\"persistent\\": { \\"cluster.max_shards_per_node\\": 1000 } }`"]'
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Logstash Pipeline",
                subject="Validation Failed: this action would add [1] shards",
                body="Alert! We can't create today's daily log indices! Elasticsearch throws `Validation Failed: 1: this action would add [1] shards, but this cluster currently has [X]/[1] maximum normal shards in the cluster`. Please raise the global shards limit!",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. No snapshot repository is configured."}

    if scenario_stage == 12:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 12:
                current_user.current_stage = 13
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_13_destructive_actions()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 13).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Destructive Actions Blocked",
                    description="Allow destructive actions to be performed with wildcards again.",
                    difficulty=models.ScenarioDifficulty.MEDIUM,
                    stage_order=13,
                    validation_type="check_destructive",
                    hints='["It seems `action.destructive_requires_name` is set to `true`.", "Use `PUT /_cluster/settings` to set it to `false`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="SRE Team",
                subject="Cronjobs failing: Destructive requires name",
                body="Hey, our nightly index cleanup cronjob is failing. It tries to delete `old-logs-*` but Elasticsearch throws an error saying destructive actions require a name. Can you lift this cluster-level restriction?",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. Shard limits are still restricted."}

    if scenario_stage == 13:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 13:
                current_user.current_stage = 14
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_14_max_result_window()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 14).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Deep Pagination Failure",
                    description="Increase the max result window for the customers index.",
                    difficulty=models.ScenarioDifficulty.EASY,
                    stage_order=14,
                    validation_type="check_max_result",
                    hints='["Deep pagination failed because we requested an offset past the default limit.", "Increase `index.max_result_window` to something large like `10000` via `PUT /customers-2026.01/_settings`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="Frontend Team",
                subject="Pagination broken on Customers page",
                body="When users go past page 10 on the customers list, the API returns a 500 error about Result Window. Someone must have accidentally lowered `max_result_window` to 100 on `customers-2026.01`. Please fix it.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. Destructive actions are still restricted."}

    if scenario_stage == 14:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 14:
                current_user.current_stage = 15
            
            ticket.status = models.TicketStatus.IN_PROGRESS

            trigger_scenario_15_allocation_awareness()
            scenario = db.query(models.Scenario).filter(models.Scenario.stage_order == 15).first()
            if not scenario:
                scenario = models.Scenario(
                    title="Allocation Awareness Limits",
                    description="Remove the hardware restriction to allow the index to allocate.",
                    difficulty=models.ScenarioDifficulty.HARD,
                    stage_order=15,
                    validation_type="check_allocation_awareness",
                    hints='["The index requires a node with `data: cold` box type, but we only have 1 node.", "Use `PUT /archive-logs-2026/_settings` to set `index.routing.allocation.require.box_type` to `null`."] '
                )
                db.add(scenario)
                db.commit()
            
            ticket = models.Ticket(
                scenario_id=scenario.id,
                player_id=current_user.id,
                sender_name="ILM Policy Engine",
                subject="Unassigned Shards on Archive Logs",
                body="The `archive-logs-2026` index is perpetually yellow/red. It looks like it's trying to allocate to a node with `box_type: cold`, but we don't have any cold nodes in this cluster right now! Please remove the routing requirement from the index settings.",
                status=models.TicketStatus.OPEN,
                hints=scenario.hints
            )
            db.add(ticket)
            db.commit()
            return {"success": True, "message": "Stage skipped. Next scenario unlocked!"}
        else:
            return {"success": False, "message": "Validation failed. Max result window is too small."}

    if scenario_stage == 15:
        is_valid = True
        if is_valid:
            if current_user.current_stage == 15:
                current_user.current_stage = 16
            
            ticket.status = models.TicketStatus.IN_PROGRESS
                
            db.commit()
            return {"success": True, "message": "Skips completed."}
        else:
            return {"success": False, "message": "Validation failed. The allocation requirement is still active."}

    return {"success": True, "message": "You have completed the available testing stages!"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
