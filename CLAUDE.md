# Claude Code Instructions for MAI Project

## Development Environment

This project runs in Docker containers. The main services are:
- `mai-api` - FastAPI backend (port 8000)
- `mai-frontend` - React/Vite frontend served via nginx (port 3000)
- `mai-gui` - Gradio GUI (port 7860, optional profile)
- `postgres` - PostgreSQL with pgvector (port 5432)
- `qdrant` - Vector database (port 6333)
- `redis` - Cache (port 6379)

## Standard Operating Procedures

### After Making Frontend Changes

The frontend runs as a production build inside a Docker container. After editing frontend code:

1. Rebuild and restart the container:
   ```bash
   docker compose build mai-frontend && docker compose up -d mai-frontend
   ```

2. Verify the container is healthy:
   ```bash
   docker compose ps mai-frontend
   ```

### After Making Backend Changes

The backend container also needs to be rebuilt after code changes:

```bash
docker compose build mai-api && docker compose up -d mai-api
```

### Viewing Logs

```bash
docker compose logs -f mai-frontend  # Frontend logs
docker compose logs -f mai-api       # Backend logs
```

### Docker Credential Issue Workaround

If you encounter `docker-credential-desktop` errors during builds, temporarily remove the `credsStore` line from `~/.docker/config.json`, build, then restore it.

## Project Structure

- `/frontend` - React/TypeScript frontend with Vite, shadcn/ui, Zustand
- `/src` - Python FastAPI backend with agents, services, and API routes
- `/docker-compose.yml` - Main container orchestration

## Key Frontend Files

- `frontend/src/stores/chatStore.ts` - Zustand store for chat sessions and messages
- `frontend/src/pages/ChatPage.tsx` - Main chat page with URL-based session routing
- `frontend/src/components/sidebar/Sidebar.tsx` - Session list and navigation
