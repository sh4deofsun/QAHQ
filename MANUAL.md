# QAHQ User Manual

Welcome to **QAHQ** (Quality Assurance Headquarters), a centralized platform for managing QA operations, distributed test execution, and result analysis.

## Table of Contents
1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
    - [Backend Setup](#backend-setup)
    - [Frontend Setup](#frontend-setup)
4. [Configuration](#configuration)
5. [Running the System](#running-the-system)
6. [Worker Deployment](#worker-deployment)
7. [Usage Guide](#usage-guide)
8. [Troubleshooting](#troubleshooting)

---

## System Overview

QAHQ consists of three main components:
- **Backend (HQ)**: A FastAPI-based server that manages authentication, database, and worker coordination.
- **Frontend**: A React + Vite web dashboard for users to interact with the system.
- **Workers**: Distributed agents that run on remote servers, execute commands/tests, and report back to HQ via WebSockets.

## Prerequisites

- **Python 3.8+**
- **Node.js 16+** & **npm**
- **Git**

## Installation

### Backend Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd QAHQ
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Initialize the database:
   The database (`qahq.db`) is automatically created when you first run the application.

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

## Configuration

### Environment Variables
You can configure the backend using environment variables. Create a `.env` file in the root directory (or set them in your shell):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret key for JWT signing. **REQUIRED** for persistent sessions. If missing, a random key is generated on startup. | (Randomly Generated) |
| `LDAP_SERVER_URL` | URL of your LDAP server | `ldap://localhost:389` |
| `LDAP_BIND_DN` | DN for LDAP binding | `cn=admin,dc=example,dc=com` |
| `LDAP_BIND_PASSWORD` | Password for LDAP binding | `admin` |
| `LDAP_USE_SSL` | Use LDAPS (`True`/`False`) | `False` |

## Running the System

### 1. Start the Backend
From the project root:
```bash
uvicorn QAHQ.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at `http://localhost:8000`.
API Documentation (Swagger UI) is at `http://localhost:8000/docs`.

### 2. Start the Frontend
From the `frontend/` directory:
```bash
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

## Worker Deployment

To connect a remote machine as a worker:

1. Ensure the machine has Python installed.
2. Copy the `QAHQ/Applications/WorkerManager/worker_client.py` file to the remote machine.
3. Install `websockets`:
   ```bash
   pip install websockets
   ```
4. Edit `worker_client.py` to point to your HQ server IP:
   ```python
   HQ_URL = "ws://<YOUR_HQ_IP>:8000/ws/worker"
   ```
5. Run the worker:
   ```bash
   python worker_client.py
   ```

The worker should now appear in the QAHQ Dashboard.

## Usage Guide

### Logging In
- Open the frontend (`http://localhost:5173`).
- **Default Admin**:
  - Username: `admin`
  - Password: `admin` (Note: This is seeded by the `verify_system.py` script or on first run if configured).
- **LDAP Users**: Use your corporate credentials if LDAP is configured.

### Dashboard
- **Active Workers**: Shows the count of currently connected workers.
- **Worker List**: Displays details for each worker (Client ID, Capabilities).
- **Run Command**: Click the "Run Command" button on a worker card to execute a shell command on that machine.

### Test Results
- (Future Feature) The system is designed to parse RobotFramework `output.xml` files.
- Upload XML files to the backend endpoints (via API or future UI) to populate test statistics.

## Troubleshooting

- **Login Failed**: Check if the `admin` user exists. Run `python verify_system.py` to seed the admin user if needed.
- **Worker Not Connecting**: Ensure the worker machine can reach the HQ server's IP and port 8000. Check firewalls.
- **CORS Errors**: If the frontend cannot talk to the backend, ensure `CORSMiddleware` in `main.py` includes your frontend's URL.
