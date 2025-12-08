#!/usr/bin/env python3
"""MLX-LM Server Manager Service.

A lightweight FastAPI service for managing the MLX-LM server process.
Runs on the host (port 8082) to bridge the frontend UI and the MLX-LM server.
"""

import json
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration
CONFIG_DIR = Path.home() / ".mai"
CONFIG_FILE = CONFIG_DIR / "mlx-config.json"
DEFAULT_MLX_PORT = 8081
DEFAULT_MLX_HOST = "127.0.0.1"
DEFAULT_MODELS_DIR = "/Volumes/the-eagle/maxwell-ext/lmstudio/models/mlx-community"

app = FastAPI(title="MLX-LM Manager", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class MLXStatus(BaseModel):
    running: bool
    pid: Optional[int] = None
    model: Optional[str] = None
    port: int = DEFAULT_MLX_PORT
    uptime_seconds: Optional[float] = None
    health_ok: bool = False


class MLXConfig(BaseModel):
    models_directory: str = DEFAULT_MODELS_DIR
    port: int = DEFAULT_MLX_PORT
    host: str = DEFAULT_MLX_HOST
    current_model: Optional[str] = None


class MLXModel(BaseModel):
    name: str
    path: str
    size: str


class StartRequest(BaseModel):
    model: str


class ConfigUpdate(BaseModel):
    models_directory: Optional[str] = None
    port: Optional[int] = None
    host: Optional[str] = None


class ActionResponse(BaseModel):
    success: bool
    message: str


# Global state
_mlx_process: Optional[subprocess.Popen] = None
_mlx_start_time: Optional[datetime] = None
_current_model: Optional[str] = None


def load_config() -> MLXConfig:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return MLXConfig(**data)
        except Exception:
            pass
    return MLXConfig()


def save_config(config: MLXConfig) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config.model_dump(), indent=2))


async def check_mlx_health(port: int = DEFAULT_MLX_PORT) -> tuple[bool, Optional[str]]:
    """Check if MLX-LM server is healthy and get model info."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # Check health
            health_resp = await client.get(f"http://127.0.0.1:{port}/health")
            if health_resp.status_code != 200:
                return False, None

            # Get model info
            models_resp = await client.get(f"http://127.0.0.1:{port}/v1/models")
            if models_resp.status_code == 200:
                data = models_resp.json()
                models = data.get("data", [])
                if models:
                    return True, models[0].get("id")
            return True, None
    except Exception:
        return False, None


def find_mlx_process(port: int = DEFAULT_MLX_PORT) -> Optional[int]:
    """Find PID of process listening on MLX port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


def get_directory_size(path: Path) -> str:
    """Get human-readable size of directory."""
    try:
        result = subprocess.run(
            ["du", "-sh", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.split()[0]
    except Exception:
        pass
    return "unknown"


@app.get("/status", response_model=MLXStatus)
async def get_status():
    """Get MLX-LM server status."""
    global _mlx_process, _mlx_start_time, _current_model

    config = load_config()
    port = config.port

    # Check if our managed process is still running
    if _mlx_process is not None:
        poll_result = _mlx_process.poll()
        if poll_result is not None:
            # Process has terminated
            _mlx_process = None
            _mlx_start_time = None

    # Check for any process on the port
    pid = find_mlx_process(port)
    health_ok, detected_model = await check_mlx_health(port)

    uptime = None
    if _mlx_start_time and pid:
        uptime = (datetime.now() - _mlx_start_time).total_seconds()

    return MLXStatus(
        running=pid is not None,
        pid=pid,
        model=detected_model or _current_model,
        port=port,
        uptime_seconds=uptime,
        health_ok=health_ok,
    )


@app.post("/start", response_model=ActionResponse)
async def start_server(request: StartRequest):
    """Start MLX-LM server with specified model."""
    global _mlx_process, _mlx_start_time, _current_model

    config = load_config()

    # Check if already running
    existing_pid = find_mlx_process(config.port)
    if existing_pid:
        return ActionResponse(
            success=False,
            message=f"Server already running on port {config.port} (PID: {existing_pid}). Stop it first.",
        )

    # Resolve model path
    model_path = Path(config.models_directory) / request.model
    if model_path.exists():
        model_arg = str(model_path)
    else:
        # Fall back to HuggingFace Hub
        model_arg = f"mlx-community/{request.model}"

    try:
        # Start the server
        _mlx_process = subprocess.Popen(
            [
                "mlx_lm.server",
                "--model", model_arg,
                "--host", config.host,
                "--port", str(config.port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        _mlx_start_time = datetime.now()
        _current_model = request.model

        # Update config with current model
        config.current_model = request.model
        save_config(config)

        # Wait briefly and check if it started
        time.sleep(2)
        if _mlx_process.poll() is not None:
            # Process died immediately
            stderr = _mlx_process.stderr.read().decode() if _mlx_process.stderr else ""
            _mlx_process = None
            _mlx_start_time = None
            return ActionResponse(
                success=False,
                message=f"Server failed to start: {stderr[:500]}",
            )

        return ActionResponse(
            success=True,
            message=f"Started MLX-LM server with model {request.model} on port {config.port}",
        )

    except FileNotFoundError:
        return ActionResponse(
            success=False,
            message="mlx_lm.server not found. Install with: pip install mlx-lm",
        )
    except Exception as e:
        return ActionResponse(success=False, message=f"Failed to start server: {e}")


@app.post("/stop", response_model=ActionResponse)
async def stop_server():
    """Stop MLX-LM server gracefully."""
    global _mlx_process, _mlx_start_time, _current_model

    config = load_config()
    pid = find_mlx_process(config.port)

    if not pid:
        return ActionResponse(success=True, message="Server not running")

    try:
        # Try graceful shutdown first
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)

        # Check if still running
        if find_mlx_process(config.port):
            # Force kill
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)

        _mlx_process = None
        _mlx_start_time = None

        return ActionResponse(success=True, message=f"Stopped server (PID: {pid})")

    except ProcessLookupError:
        _mlx_process = None
        _mlx_start_time = None
        return ActionResponse(success=True, message="Server already stopped")
    except Exception as e:
        return ActionResponse(success=False, message=f"Failed to stop server: {e}")


@app.post("/restart", response_model=ActionResponse)
async def restart_server(request: Optional[StartRequest] = None):
    """Restart MLX-LM server, optionally with a new model."""
    global _current_model

    # Stop current server
    stop_result = await stop_server()
    if not stop_result.success and "not running" not in stop_result.message.lower():
        return stop_result

    # Wait for port to be released
    config = load_config()
    for _ in range(10):
        if not find_mlx_process(config.port):
            break
        time.sleep(0.5)

    # Start with new or current model
    model = request.model if request else (_current_model or config.current_model)
    if not model:
        return ActionResponse(
            success=False,
            message="No model specified and no previous model to restart with",
        )

    return await start_server(StartRequest(model=model))


@app.get("/models", response_model=list[MLXModel])
async def list_models():
    """List available MLX models in the configured directory."""
    config = load_config()
    models_dir = Path(config.models_directory)

    if not models_dir.exists():
        return []

    models = []
    for item in sorted(models_dir.iterdir()):
        if item.is_dir():
            # Check for config.json (indicates valid MLX model)
            config_file = item / "config.json"
            if config_file.exists():
                models.append(
                    MLXModel(
                        name=item.name,
                        path=str(item),
                        size=get_directory_size(item),
                    )
                )

    return models


@app.get("/config", response_model=MLXConfig)
async def get_config():
    """Get current configuration."""
    return load_config()


@app.post("/config", response_model=MLXConfig)
async def update_config(update: ConfigUpdate):
    """Update configuration."""
    config = load_config()

    if update.models_directory is not None:
        config.models_directory = update.models_directory
    if update.port is not None:
        config.port = update.port
    if update.host is not None:
        config.host = update.host

    save_config(config)
    return config


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8082)
