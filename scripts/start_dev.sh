echo "starting development environment..."

docker compose -f docker-compose.dev.yml --profile uns up -d --build

echo "Development environment started. Press Ctrl+C to stop log streaming."
trap 'echo; echo "Stopping log stream..."; ' INT
docker logs -f uns-dev || true
trap - INT

echo stopping development environment...
docker compose -f docker-compose.dev.yml --profile uns down
echo "Development environment stopped."
