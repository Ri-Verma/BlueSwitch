from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel
import docker
import webbrowser                           
import threading                            
import time

app = FastAPI()

class EnvPayload(BaseModel):
    variables: dict

# This allows the Frontend to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory="dashboard", html=True), name="ui")

client = docker.from_env()

def ensure_proxy_running():
    """Ensures the paas-proxy container is created and running on startup."""
    print("--- Checking PaaS Infrastructure ---")
    
    # 1. Ensure the network exists first
    try:
        client.networks.get("paas-network")
    except docker.errors.NotFound:
        print("Creating 'paas-network'...")
        client.networks.create("paas-network")

    # 2. Check on the Proxy container
    try:
        proxy = client.containers.get("paas-proxy")
        if proxy.status != "running":
            print("Starting existing 'paas-proxy'...")
            proxy.start()
        else:
            print("'paas-proxy' is already running safely.")
            
    except docker.errors.NotFound:
        print("Proxy not found. Creating and starting 'paas-proxy'...")
        try:
            client.containers.run(
                "nginx:alpine",
                name="paas-proxy",
                detach=True,
                network="paas-network",
                ports={'80/tcp': 80},
                volumes={
                    '/home/hiori/Desktop/WorkStation/MVP/PaaS_System/proxy/conf.d': {
                        'bind': '/etc/nginx/conf.d',
                        'mode': 'rw' # rw -> read/write
                    },
                    # 🆕 NEW: Mount the HTML folder so Nginx can see your 502 error page
                    '/home/hiori/Desktop/WorkStation/MVP/PaaS_System/proxy/html': {
                        'bind': '/usr/share/nginx/html',
                        'mode': 'ro' # ro -> read-only
                    }
                }
            )
            print("Proxy created successfully!")
        except Exception as e:
            print(f"Failed to create proxy: {e}")

# Call the function immediately so it runs when the script starts
ensure_proxy_running()


# ---------------------------------------------------------
# 1. LIVE RESOURCE METRICS (The Monitor)
# ---------------------------------------------------------
@app.get("/api/apps/{name}/stats")
def get_app_stats(name: str):
    """Fetches real-time memory usage from the Docker engine."""
    try:
        container = client.containers.get(name)
        stats = container.stats(stream=False)
        
        # Calculate Memory Usage in Megabytes
        mem_usage = stats['memory_stats'].get('usage', 0)
        mem_limit = stats['memory_stats'].get('limit', 1)
        
        return {
            "usage_mb": round(mem_usage / (1024 * 1024), 2),
            "limit_mb": round(mem_limit / (1024 * 1024), 2)
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------
# 2. ENVIRONMENT VARIABLE MANAGER (The Secret Keeper)
# ---------------------------------------------------------
@app.post("/api/apps/{name}/env")
def update_env_vars(name: str, payload: EnvPayload):
    """Saves secure variables to a .env file in the deployment folder."""
    # We save these to the folder where your bash script builds the app
    env_file_path = "/home/hiori/Desktop/WorkStation/MVP/PaaS_System/deployed-app/.env"
    
    try:
        with open(env_file_path, "w") as f:
            for key, value in payload.variables.items():
                f.write(f"{key}={value}\n")
        return {"message": "Secrets saved successfully! Re-deploy to apply."}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------
# 3. THE DANGER ZONE (App Deletion)
# ---------------------------------------------------------
@app.delete("/api/apps/{name}")
def delete_app(name: str):
    """Completely destroys an application and its routing rules."""
    try:
        # 1. Kill and remove the container
        container = client.containers.get(name)
        container.stop()
        container.remove()
        
        # 2. Delete the Nginx routing configuration
        conf_path = f"/home/hiori/Desktop/WorkStation/MVP/PaaS_System/proxy/conf.d/{name}.conf"
        if os.path.exists(conf_path):
            os.remove(conf_path)
            
        # 3. Reload the Proxy to sever the connection permanently
        proxy = client.containers.get("paas-proxy")
        proxy.exec_run("nginx -s reload")
        
        return {"message": f"App {name} has been completely annihilated."}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/apps")
def get_apps():
    """Fetches all PaaS-related containers."""
    containers = client.containers.list(all=True)
    result = []
    
    for c in containers:
        try:
            # We only care about our PaaS proxy and the deployed apps
            if c.name.startswith("app") or c.name == "paas-proxy":
                # By reading c.status or c.name, we trigger Docker. 
                # If the container was just deleted by Bash, this will throw an error.
                result.append({
                    "id": c.short_id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown"
                })
        except docker.errors.NotFound:
            # THE FIX: If the container was deleted mid-loop by our zero-downtime script, 
            # we just quietly skip it and move to the next one!
            continue
        except Exception as e:
            # Catch any other random errors so they don't crash the whole API
            print(f"Error reading container: {e}")
            continue
            
    return result

@app.post("/api/apps/{name}/stop")
def stop_app(name: str):
    """Command to stop a specific app via the UI"""
    container = client.containers.get(name)
    container.stop()
    return {"message": f"App {name} stopped"}

@app.post("/api/apps/{name}/start")
def start_app(name: str):
    """Command to start a specific app via the UI"""
    try:
        container = client.containers.get(name)
        container.start()
        return {"message": f"App {name} started successfully"}
    except Exception as e:
        return {"error": str(e)}

def open_browser():
    """Waits for the server to boot, then opens the dashboard."""
    time.sleep(1.5) 
    print("Opening Dashboard...")
    webbrowser.open("http://127.0.0.1:8000/ui")

if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)