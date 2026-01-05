# Project in progress
# Log Management Platform

A comprehensive platform that simulates a production environment for Elasticsearch, featuring log generation, processing, storage, and monitoring capabilities.

## Architecture

- **Elasticsearch**: Stores and indexes logs
- **Logstash**: Processes and enriches logs before indexing
- **Kibana**: Visual analytics and dashboard (accessible at http://localhost:5601)
- **FastAPI Backend**: REST API for log management and querying
- **Log Generators**: Simulate various types of production logs
- **Chaos Engine**: Simulates cluster failures and security incidents for testing
- **Frontend Dashboard**: Web-based UI for log viewing and analysis
