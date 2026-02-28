# Elastic Simulator Platform

An interactive, level-based simulation platform designed to train engineers in Elasticsearch and Log Management. The platform simulates a realistic production environment using the ELK stack (v8.x), complete with client traffic, simulated anomalies, cluster failures, and security incidents.

## Architecture

The platform consists of the following core components:

1. **Game Engine API (FastAPI)**
   - Manages the user's progression through different stages (Easy to Hard).
   - Periodically evaluates the state of the ELK cluster to check if the user has successfully resolved the current problem.
   - Serves the frontend where users receive "messages" and "tickets" from clients.
   - Commands the Log Generator and Infrastructure Orchestrator to transition to the next state when a stage is solved.

2. **Relational Database (PostgreSQL)**
   - Stores game state: Player profiles, their progression, generated incident tickets, and simulated user data (the clients complaining about issues).

3. **Log Generator (Python)**
   - A background worker that simulates diverse client applications sending logs to the Elasticsearch cluster.
   - Injects specific patterns into the logs depending on the active scenario (e.g., spikes in `500` errors, malicious IP addresses, or malformed logs).

4. **Infrastructure Orchestrator (Docker SDK for Python)**
   - Spins up the ELK stack (Elasticsearch, Logstash, Kibana) using Docker.
   - Simulates cluster-level problems physically (e.g., dynamically pausing a node container to simulate network partition, or artificially filling up disk space to trigger a high watermark alert).

5. **Interactive UI (React)**
   - A realistic dashboard where the user receives incoming bug reports (e.g., a simulated Slack or ticketing interface).
   - Displays the current objective, hints, and cluster health overview.

6. **The Target Environment (ELK Stack 8.x)**
   - The actual Elasticsearch cluster that the user will interact with, debug, and fix using standard tools like Kibana Dev Tools or the Elasticsearch REST API.

## Stage Mechanics

The scenarios are ranked progressively from Easy to Hard. 
- **Trigger**: The stage starts with an event and a notification. For example, a "Slack-like" message from a simulated developer: *"Hey, my logs from the billing service aren't showing up in Kibana since this morning!"*
- **Investigation**: The user uses Kibana to diagnose the root cause.
- **Resolution**: The Game Engine constantly checks the Elasticsearch cluster state (e.g., querying for unassigned shards or verifying if a specific index template is fixed).
- **Advancement**: Once validated, the system congratulates the user and advances to the next stage, triggering new cluster changes and log patterns.

### Example Scenarios

- **Easy**: Index mapping constraints, incorrect Logstash grok patterns, or parsing errors.
- **Medium**: High disk watermarks causing read-only indices, dead nodes, or mapping explosions.
- **Hard**: Complex security incidents (detecting ransomware patterns or lateral movement), split-brain cluster recovery, or restoring corrupted snapshots.

## Tech Stack

- **Backend core**: Python 3.10+, FastAPI, SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: React (Vite)
- **Log Generator**: Python (utilizing the `elasticsearch` python client and `Faker` library)
- **Infrastructure**: Docker, Docker Compose, Docker SDK for Python
- **Environment**: Elasticsearch 8.x, Kibana 8.x, Logstash 8.x

## Getting Started

*(Instructions to be added as project develops)*
