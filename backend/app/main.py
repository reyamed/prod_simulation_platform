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
    db_player = db.query(models.Player).filter(models.Player.email == player.email).first()
    if db_player:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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

from .orchestrator import validate_stage_1, validate_stage_2, validate_stage_3, validate_stage_4, trigger_scenario_2_replicas, trigger_scenario_3_data_view, trigger_scenario_4_hard_disk_watermark

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
def validate_game(current_user: models.Player = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.current_stage == 1:
        is_valid = validate_stage_1()
        if is_valid:
            current_user.current_stage = 2
            current_user.score += 100
            
            for t in db.query(models.Ticket).filter(models.Ticket.player_id == current_user.id, models.Ticket.status == models.TicketStatus.OPEN).all():
                t.status = models.TicketStatus.RESOLVED

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
            
    if current_user.current_stage == 2:
        is_valid = validate_stage_2()
        if is_valid:
            current_user.current_stage = 3
            current_user.score += 150
            
            for t in db.query(models.Ticket).filter(models.Ticket.player_id == current_user.id, models.Ticket.status == models.TicketStatus.OPEN).all():
                t.status = models.TicketStatus.RESOLVED

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

    if current_user.current_stage == 3:
        is_valid = validate_stage_3()
        if is_valid:
            current_user.current_stage = 4
            current_user.score += 200
            
            for t in db.query(models.Ticket).filter(models.Ticket.player_id == current_user.id, models.Ticket.status == models.TicketStatus.OPEN).all():
                t.status = models.TicketStatus.RESOLVED

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
            
    if current_user.current_stage == 4:
        is_valid = validate_stage_4()
        if is_valid:
            current_user.current_stage = 5
            current_user.score += 500
            
            for t in db.query(models.Ticket).filter(models.Ticket.player_id == current_user.id, models.Ticket.status == models.TicketStatus.OPEN).all():
                t.status = models.TicketStatus.RESOLVED
                
            db.commit()
            return {"success": True, "message": "Congratulations! You completed the Elastic Simulator."}
        else:
            return {"success": False, "message": "Validation failed. The disk watermark flood stage blocks are still active."}
    
    return {"success": True, "message": "You have completed the available testing stages!"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
