# SpecGen AI

SpecGen AI is a full-stack web application that assists in drafting Software Requirement Specifications (SRS) from natural language project ideas. It automatically categorizes the domain, generates numbered functional requirements with MoSCoW prioritization, drafts user stories and use cases, estimates initial sprint distribution, and exports documents to PDF and Word.

Built with a FastAPI backend, React (Vite) frontend, and packaged with Docker, Jenkins CI/CD on AWS EC2, and Kubernetes (Minikube).

---

## Architecture & Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy (SQLite), Pydantic v2, ReportLab / python-docx.
- **Frontend:** React 18, Vite, React Router 6, Tailwind CSS.
- **Testing:** Pytest (73 automated unit and integration tests).
- **DevOps & Cloud:**
  - **CI/CD:** Jenkins LTS running on AWS EC2.
  - **Containerization:** Multi-stage Docker build (`node:20-alpine` + `python:3.11-slim`).
  - **Registry:** Docker Hub (`zainuls/specgen-ai`).
  - **Orchestration:** Kubernetes (Minikube) with Deployment (4 replicas, rolling update) and NodePort Service.

---

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── routers/          # auth, projects, admin routes
│   │   ├── ai_engine.py      # LLM generation & heuristic fallbacks
│   │   ├── auth.py           # JWT token handling & password hashing
│   │   ├── database.py       # SQLAlchemy engine & session
│   │   ├── export.py         # PDF & DOCX export builders
│   │   ├── main.py           # FastAPI entrypoint, healthcheck & SPA mount
│   │   ├── models.py         # DB models
│   │   ├── planning.py       # Deterministic sprint planning logic
│   │   ├── review.py         # Ambiguity and duplicate requirement checks
│   │   └── schemas.py        # Pydantic schemas
│   ├── tests/                # 73 automated test cases
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/            # Login, Register, Dashboard, ProjectView, Admin
│   │   ├── api.js            # Axios client
│   │   └── App.jsx           # Main routing component
│   └── package.json
├── k8s/
│   ├── deployment.yaml       # Kubernetes Deployment (replicas, rolling update, probes)
│   └── service.yaml          # NodePort Service (exposes port 30080)
├── Dockerfile                # Multi-stage production container build
├── Jenkinsfile               # Declarative 6-stage CI/CD pipeline
├── README.md
└── DEPLOYMENT_REPORT.md      # CCA 2 deployment report and viva guide
```

---

## Local Setup

### 1. Backend

```bash
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API docs are available at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs at `http://localhost:5173`.

### 3. Running Automated Tests

```bash
cd backend
pytest tests/ -v
```

All 73 unit and integration tests run locally without requiring live external LLM API keys (using mock/deterministic heuristics).

---

## Docker & Containerization

The multi-stage `Dockerfile` compiles the Vite React frontend into static assets and bundles them directly into the FastAPI application, serving everything from a single container on port 8000.

```bash
# Build the image
docker build -t zainuls/specgen-ai:latest .

# Run the container
docker run -d -p 8000:8000 --name specgen-ai zainuls/specgen-ai:latest

# Check health endpoint
curl http://localhost:8000/health
```

---

## Kubernetes Deployment (Minikube)

The application is deployed to Kubernetes using the manifests in `k8s/`:

```bash
# Apply deployment and service
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Scale replicas
kubectl scale deployment specgen-ai --replicas=4

# Check status
kubectl get pods,svc -o wide

# Access service
kubectl port-forward svc/specgen-ai-service 30080:8000
```

Open `http://localhost:30080` in your browser.

---

## CI/CD Pipeline (Jenkins)

The pipeline is defined in `Jenkinsfile` and runs automatically on AWS EC2 Jenkins:

1. **Checkout:** Pulls latest code from GitHub.
2. **Build & Test:** Runs the 73-test pytest suite in a clean virtual environment.
3. **Docker Build:** Builds the multi-stage image tagged with `${BUILD_NUMBER}` and `latest`.
4. **Push Image:** Authenticates with Docker Hub using Jenkins credentials and pushes the image tags.
5. **Minikube Deployment:** Applies Kubernetes manifests and triggers a rolling update.
6. **Verification:** Inspects pod status, rollout state, and verifies `GET /health`.
