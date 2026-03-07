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

Follow these instructions to set up the Elastic Simulator Platform on your local machine for development and testing purposes.

### Prerequisites

Ensure you have the following installed on your system:
- **Docker & Docker Compose**: Required for standing up the Elasticsearch, Kibana, and PostgreSQL instances.
- **Python 3.10+**: Required for the FastAPI backend and Log Generator.
- **Node.js 18+ & npm**: Required for the React development server and frontend testing.
- **Git**: For version control.

### Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/reyamed/prod_simulation_platform.git
   cd prod_simulation_platform
   ```

2. **Start Infrastructure Services**
   The platform relies on containerized databases and search engines. Spin them up using Docker Compose:
   ```bash
   docker-compose up -d
   ```
   *Note: Ensure you have sufficient allocated RAM in your Docker desktop settings, as Elasticsearch is memory-intensive.*

3. **Backend Setup**
   Navigate to the backend directory, create a virtual environment, and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Frontend Setup**
   Navigate to the frontend directory and install the required Node modules:
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

1. **Start the Backend Server**
   From the `backend` directory, with your virtual environment activated, run the Uvicorn server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The API will be available at `http://localhost:8000` (interactive documentation at `/docs`).

2. **Start the Frontend Development Server**
   From the `frontend` directory, start Vite:
   ```bash
   npm run dev
   ```
   Access the user interface at `http://localhost:5173`.

### Testing Pipeline

The project implements a modern, comprehensive testing suite to ensure stability across the stack.

- **Backend Integration & Unit Tests (Pytest)**
  ```bash
  cd backend
  pytest tests/
  ```
- **Frontend Unit Tests (Vitest & React Testing Library)**
  ```bash
  cd frontend
  npx vitest run
  ```
- **End-to-End Tests (Playwright)**
  Playwright verifies the critical path by simulating real browser interactions. Ensure both the frontend and backend servers are running, then execute:
  ```bash
  cd e2e
  npx playwright test
  ```

### Continuous Integration (CI)

This repository includes a robust GitHub Actions pipeline (`.github/workflows/ci.yml`) that automatically evaluates the code on every push or pull request to the `develop` and `main` branches. It validates backend compliance, frontend modularity, and executes end-to-end user flows.
