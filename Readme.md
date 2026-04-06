# Mini-PaaS: Local Platform as a Service

A lightweight, localized Platform as a Service (PaaS) built from scratch using Python, Docker, Nginx, and Git Hooks. This project provides a Heroku/Vercel-like developer experience on a local machine, featuring a custom Control Plane, automated CI/CD, and Zero-Downtime Blue/Green deployments.

## Key Features

* **Zero-Downtime Deployments:** Uses a Blue/Green strategy to spin up new Docker containers and dynamically reload Nginx routing rules with zero dropped requests.
* **Automated CI/CD:** Powered by Git Hooks (`post-receive`). Pushing code automatically builds, tags, and deploys the application.
* **Control Plane Dashboard:** A decoupled FastAPI backend and Vanilla JS frontend for real-time monitoring and container orchestration.
* **Secret Management:** Inject secure Environment Variables directly into running containers via the UI.
* **Self-Healing Infrastructure:** Built-in health checks, automated container restarts, and custom 502 Graceful Fallback pages if an app goes offline.
* **Live UI Reloading:** The frontend automatically detects deployment swaps and refreshes the browser without manual intervention.

---

## Architecture & Directory Structure

The workspace is strictly decoupled into the Platform (`BlueSwitch`) and the Client Application (`demo-website`).

```text
Home/
├── BLueSwitch/            # The Platform Infrastructure
│   ├── main.py             # FastAPI Control Plane Server
│   ├── dashboard/          # Frontend UI assets (index.html, js, css)
│   ├── proxy/              # Nginx configuration and 502 Fallback HTML
│   ├── app.git/            # Bare Git repository (Receives pushed code)
│   │   └── hooks/post-receive # The Blue/Green deployment Bash script
│   └── deployed-app/       # Auto-generated extraction zone for Docker builds
│
└── demo-website/           # Example Client Application
    ├── Dockerfile          # Instructions to containerize the app
    ├── index.html          # App source code
    ├── style.css           # App styling
    └── script.js           # App logic
```

---

## Setup Instructions

### Prerequisites
Ensure you have the following installed on your local machine:
* **Docker Engine** (running locally)
* **Python 3.10+**
* **Git**

### Step 1: Initialize the Control Plane
1. Open your terminal and navigate to the PaaS directory:
   ```bash
   cd Your-project
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required backend dependencies:
   ```bash
   pip install fastapi uvicorn docker pydantic
   ```
4. Start the Control Plane Server:
   ```bash
   python3 main.py
   ```
   *The server will boot up, verify the Docker network, ensure the Nginx proxy is running, and automatically open the Dashboard at `http://127.0.0.1:8000/ui`.*

### Step 2: Configure the Client Application
1. Open a new terminal window and navigate to your client application folder:
   ```bash
   cd builds/demo-website
   ```
2. Add the PaaS as a Git remote destination (make sure to use your absolute path):
   ```bash
   git remote add local /absolute/path/your-project/app.git
   ```

### Step 3: Deploy via Git
Make a change to your app, commit it, and push to the PaaS server:
```bash
git add .
git commit -m "Initial Deployment"
git push local master
```
*Watch the terminal as the Git Hook automatically builds the Docker image, starts the container, and switches the Nginx proxy traffic with zero downtime. Your app will be live at `http://app.local`.*

*By default, the Nginx reverse proxy routes traffic based on the application name, assuming a .local domain. To access http://app.local on your browser, you must map it to your local machine.*

*Add the following line to your operating system's hosts file:
127.0.0.1 app.local *

*Linux/Mac: Edit /etc/hosts (requires sudo).*

*Windows: Edit C:\Windows\System32\drivers\etc\hosts (requires running Notepad as Administrator).*

---

## Secret Management (.env)

A core feature of this platform is the ability to securely manage Environment Variables (Secrets) without hardcoding them into your application's GitHub repository.

### How to add Secrets via the UI:
1. Open the BlueSwitch Control Plane Dashboard (`http://127.0.0.1:8000/ui`).
2. Locate your running application card.
3. Click the "Add Secret" button.
4. Enter the Variable Name (e.g., `API_KEY`) and its Value.

### How it works under the hood:
When you save a secret via the dashboard, the FastAPI backend securely writes it to the `BlueSwitch/deployed-app/.env` file. 

During the next deployment (`git push local master`), the `post-receive` bash script automatically injects this `.env` file directly into the Docker container upon startup using the `--env-file` flag:

```bash
docker run -d --name $NEW_CONTAINER --network paas-network --env-file $TARGET/.env <image-name>
```

Your application code can now securely access these variables at runtime.