import requests
import time
import subprocess
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from QAHQ.Databases import models, database
from QAHQ.Securities import auth

# Setup DB access to seed admin
engine = create_engine("sqlite:///./QAHQ/Databases/qahq.db")
SessionLocal = sessionmaker(bind=engine)

def seed_admin():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin").first()
        if not user:
            hashed_password = auth.get_password_hash("admin")
            user = models.User(username="admin", hashed_password=hashed_password, is_admin=True, auth_source="local")
            db.add(user)
            db.commit()
            print("Seeded admin user.")
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

def verify():
    base_url = "http://localhost:8000"
    
    # 1. Login
    print("Logging in...")
    try:
        response = requests.post(f"{base_url}/token", data={"username": "admin", "password": "admin"})
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful.")
    except Exception as e:
        print(f"Login error: {e}")
        return

    # 2. Check MCP Worker Status (should be empty initially)
    # Note: MCP endpoint is /mcp/tools/get_worker_status (POST)
    print("Checking worker status (expecting empty)...")
    response = requests.post(f"{base_url}/mcp/tools/get_worker_status", headers=headers)
    print(f"Worker Status: {response.json()}")

    # 3. Start Worker
    print("Starting worker...")
    worker_process = subprocess.Popen([sys.executable, "QAHQ/Applications/WorkerManager/worker_client.py"])
    time.sleep(2) # Wait for connection

    # 4. Check Worker Status again
    print("Checking worker status (expecting 1 worker)...")
    response = requests.post(f"{base_url}/mcp/tools/get_worker_status", headers=headers)
    print(f"Worker Status: {response.json()}")
    
    workers = response.json().get("workers", [])
    if not workers:
        print("No workers found!")
        worker_process.terminate()
        return
        
    client_id = workers[0]["client_id"]

    # 5. Run Command
    print(f"Running command on worker {client_id}...")
    cmd_payload = {"command": "echo 'Hello from HQ'"}
    response = requests.post(f"{base_url}/worker/{client_id}/run_command", json=cmd_payload, headers=headers)
    print(f"Command Response: {response.json()}")
    
    time.sleep(2) # Wait for execution and log (in server logs)

    print("Verification complete.")
    worker_process.terminate()

if __name__ == "__main__":
    seed_admin()
    # We assume server is running separately
    verify()
