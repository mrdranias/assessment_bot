#!/bin/bash
set -e

# PROJECT ROOT DIR (edit if not running from project root)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "==> Building and starting containers..."
docker compose up -d --build

echo "==> Waiting for PostgreSQL to be healthy..."
until docker exec adl_postgres pg_isready -U postgres -d adl_assessment
do
    sleep 2
    echo "Waiting for postgres..."
done

echo "==> Waiting for Neo4j to be healthy..."
until docker exec adl_neo4j cypher-shell -u neo4j -p password123 "RETURN 1" >/dev/null 2>&1
do
    sleep 2
    echo "Waiting for neo4j..."
done

# Activate your python venv here if needed:
# source venv/bin/activate

echo "==> Initializing PostgreSQL database with SQLAlchemy models..."
python3 scripts/seed_postgres.py

echo "==> Seeding Neo4j knowledge graph..."
python3 scripts/seed_neo4j.py

# (Optional) To load a Cypher file directly (if seed_neo4j.py is not used):
# echo "==> Running Neo4j Cypher init file..."
# docker cp db/init.cypher adl_neo4j:/init.cypher
# docker exec -u neo4j adl_neo4j cypher-shell -u neo4j -p password123 -f /init.cypher

echo "==> All services and databases are up and seeded!"
echo "==> 🏥 Clinical Dashboard: http://localhost:7860"
echo "==> 🔧 API Backend:       http://localhost:8000"
echo "==> 🗃️  PostgreSQL:        psql -h localhost -U postgres -d adl_assessment"
echo "==> 📊 Neo4j Browser:     http://localhost:7474 (user: neo4j / password123)"

# Start Jupyter Lab
#docker exec -it adl_ui bash
#jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=''

