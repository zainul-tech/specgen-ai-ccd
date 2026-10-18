# Continuous Assessment 2 (CCA 2) — Project Deployment Report
## CI/CD Pipeline Implementation and Deployment of an Existing Project
**Course:** TYCSE · Cloud Computing and DevOps (CSE20120 / CSE30040)  
**Faculty / Evaluator:** Prof. Priya Nagargoje (Total Marks: 10)  
**Student PRN / Roll Number:** [Your PRN / Roll Number]  
**GitHub Repository:** [https://github.com/zainul-tech/specgen-ai-ccd](https://github.com/zainul-tech/specgen-ai-ccd)  
**Docker Hub Repository:** [https://hub.docker.com/r/zainuls/specgen-ai](https://hub.docker.com/r/zainuls/specgen-ai)  
**AWS EC2 Jenkins Endpoint:** `http://13.220.184.51:8080`  
**Local Kubernetes Minikube Endpoints:** `http://localhost:30080` / `http://localhost:8000`  

---

### Executive Summary
This report presents the end-to-end automated delivery lifecycle for **SpecGen AI**, an AI-assisted platform for generating Software Requirements Specifications (SRS). Building upon the foundational competencies of **Experiment 4** (Docker Containerization & Registry Distribution), **Experiment 5** (Jenkins CI/CD Automation on AWS EC2), and **Experiment 6** (Container Orchestration & Scaling with Kubernetes/Minikube), this project establishes a resilient, production-grade automated pipeline adhering strictly to the CCA 2 Student Guidelines.

---

### 1. Existing Project Selection & Architecture (1 Mark)
- **Selected Project:** **SpecGen AI**
- **Domain:** AI-Assisted Software Engineering & Automated Requirement Specification Generation.
- **Backend Architecture:**
  - Framework: Python 3.11 with FastAPI.
  - Data Validation: Pydantic v2 schemas.
  - Persistence: SQLite / SQLAlchemy ORM.
  - Endpoints: RESTful APIs for user authentication, project creation, requirement analysis, and an automated liveness/readiness `/health` probe.
- **Frontend Architecture:**
  - Modern Single Page Application (SPA) built with React 18 and Vite.
  - UI styled with TailwindCSS, Lucide icons, and responsive components.
- **Automated Test Suite:**
  - 73 comprehensive unit and integration tests executing via `pytest`.
  - Tests cover authentication token issuance, input validation, project creation, AI requirement heuristic analysis, and document generation.
- **Repository Structure:**
  ```text
  specgen-ai-ccd/
  ├── backend/               # FastAPI microservice
  │   ├── app/               # Application routers, models, schemas
  │   │   ├── main.py        # Application entrypoint & /health probe
  │   │   ├── routers/       # Auth, projects, admin endpoints
  │   │   └── database.py    # Database session and SQLite engine
  │   ├── tests/             # 73 automated pytest test cases
  │   └── requirements.txt   # Runtime & dev dependencies
  ├── frontend/              # React Vite SPA
  │   ├── src/               # React components and styling
  │   └── package.json       # Node dependencies
  ├── k8s/                   # Kubernetes Manifests
  │   ├── deployment.yaml    # Deployment manifest (replicas, rolling update, health checks)
  │   └── service.yaml       # NodePort service manifest (port 8000 -> 30080)
  ├── Dockerfile             # Multi-stage container build
  ├── Jenkinsfile            # 6-stage Declarative CI/CD pipeline
  ├── README.md              # Project documentation
  └── DEPLOYMENT_REPORT.md   # Official CCA 2 deployment submission report
  ```

---

### 2. AWS Infrastructure & Jenkins CI Server Setup (1.5 Marks)
- **Cloud Provider:** Amazon Web Services (AWS) — Free Tier.
- **Instance Type:** EC2 `t2.micro` / `t3.micro` running Amazon Linux 2023.
- **Public IP:** `13.220.184.51`
- **Security Group Inbound Rules:**
  - Port `22` (SSH): Administrator access for server maintenance.
  - Port `8080` (HTTP): Jenkins automation server web console.
  - Port `30080` (TCP): Kubernetes NodePort service for application verification.
- **System Components & Software Installed on EC2:**
  - Java Development Kit: `java-21-amazon-corretto`.
  - Jenkins LTS: Version 2.580.1 running as a systemd service (`jenkins.service`).
  - Docker Engine: `docker.io` enabled and running at boot.
  - Non-privileged execution: Jenkins user added to the docker socket group (`sudo usermod -aG docker jenkins`).
  - Memory Optimization: 4 GB swap space configured at `/swapfile` to prevent out-of-memory kernel panics during multi-stage Docker builds on the free tier.
- **Jenkins Credentials:**
  - Credential ID: `dockerhub-credentials` (Type: Username with Password / Secret Access Token).
  - Credentials are securely injected at runtime into the Jenkins pipeline environment via `withCredentials` without hardcoding secrets in source control.

---

### 3. Dockerfile Multi-Stage Containerization (1.5 Marks)
To achieve minimal image size, fast deployment, and maximum security, a multi-stage Docker architecture is implemented:
- **Stage 1: Build Frontend Assets (`node:20-alpine`)**
  - Installs npm dependencies cleanly with caching.
  - Executes `npm run build` using Vite to compile the React SPA into static, minified JS/CSS assets (`dist/`).
- **Stage 2: Runtime Environment (`python:3.11-slim`)**
  - Uses an official minimal Debian Python runtime.
  - Installs backend Python dependencies without cache clutter.
  - Copies compiled frontend bundle from Stage 1 into `backend/app/static/`.
  - Exposes port `8000`.
  - Runs Uvicorn serving both the FastAPI REST endpoints and the React frontend static assets from a unified container.

---

### 4. Declarative CI/CD Jenkins Pipeline (2 Marks)
The automated workflow is declared in [`Jenkinsfile`](Jenkinsfile) and consists of 6 sequential automated stages:
1. **Stage 1 (Checkout):**
   - Pulls the latest commit from the configured GitHub repository branch (`main`).
   - Records the short commit SHA and branch name.
2. **Stage 2 (Build & Test):**
   - Prepares an isolated cached Python virtual environment (`.specgen-ci-venv`).
   - Runs `pytest tests/ -v`.
   - All 73 tests must pass before the pipeline proceeds.
3. **Stage 3 (Docker Build):**
   - Executes multi-stage container build:
     `docker build -t zainuls/specgen-ai:${BUILD_NUMBER} -t zainuls/specgen-ai:latest .`
4. **Stage 4 (Push Image to Registry):**
   - Authenticates against Docker Hub using secure Jenkins credentials (`--password-stdin`).
   - Pushes both immutable build tag (`zainuls/specgen-ai:${BUILD_NUMBER}`) and latest release tag (`zainuls/specgen-ai:latest`).
5. **Stage 5 (Minikube Deployment):**
   - Applies Kubernetes manifests (`k8s/deployment.yaml` and `k8s/service.yaml`).
   - Updates deployment container image to the newly pushed build tag.
   - Monitors rollout status (`kubectl rollout status deployment/specgen-ai`).
6. **Stage 6 (Verification):**
   - Inspects status of running pods, services, and deployments.
   - Validates live application availability via HTTP GET on the `/health` endpoint.

---

### 5. Container Registry Integration (1 Mark)
- **Registry Provider:** Docker Hub (`https://hub.docker.com/r/zainuls/specgen-ai`).
- **Tagging Strategy:**
  - Build-Specific Tags: e.g., `zainuls/specgen-ai:1`, `zainuls/specgen-ai:2`, `zainuls/specgen-ai:3` for immutable artifact tracking and rollback capabilities.
  - Latest Tag: `zainuls/specgen-ai:latest` representing the current stable release.
- **Security:** Docker Hub credentials are never stored in code, Git history, or shell history. Authentication uses tokenized credentials provided via Jenkins credential binding.

---

### 6. Kubernetes Deployment & Service on Minikube (1.5 Marks)
- **Local Cluster Platform:** Minikube v1.39.0 with Docker container driver.
- **Deployment Specification (`k8s/deployment.yaml`):**
  - **Replicas:** Configured with 2 baseline pods and scaled to 4 replicas (`kubectl scale deployment specgen-ai --replicas=4`).
  - **Zero-Downtime Strategy:** `RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 0` ensuring zero downtime during updates.
  - **Probes:** `livenessProbe` and `readinessProbe` checking the `/health` endpoint on port `8000`.
  - **Resource Requests & Limits:** Minimal resource footprint (CPU 50m / Memory 64Mi request) ensuring seamless operation on standard student hardware.
- **Service Specification (`k8s/service.yaml`):**
  - **Service Type:** `NodePort`
  - **Target Port:** `8000` (FastAPI container port)
  - **Static NodePort:** `30080` (accessible across cluster nodes and localhost).

---

### 7. Application Verification & Code-Change Demonstration (1.5 Marks)
To satisfy Criterion 7 and Experiment 5 Step 16:
1. **Initial Deployment (Version 1.0.0):**
   - Verified active pods: 4/4 pods in `Running` state with 0 restarts.
   - Verified endpoint response:
     ```json
     {"status": "ok", "app": "SpecGen AI", "version": "1.0.0", "environment": "production"}
     ```
2. **Source Code Modification:**
   - Modified `backend/app/main.py` updating the application version to `2.0.0`:
     ```python
     app = FastAPI(title="SpecGen AI", version="2.0.0")
     # ...
     @app.get("/health")
     def health():
         return {"status": "ok", "app": "SpecGen AI", "version": "2.0.0", "environment": "production"}
     ```
3. **Automated Pipeline Execution:**
   - Changes committed and pushed to GitHub `origin main`.
   - Jenkins executes automated build, tests pass, Docker container is compiled, published to Docker Hub as tag `:4` and `:latest`.
   - Kubernetes executes rolling update without dropping a single active request.
4. **Post-Deployment Verification:**
   - Verified updated endpoint response:
     ```json
     {"status": "ok", "app": "SpecGen AI", "version": "2.0.0", "environment": "production"}
     ```

---

### 8. Verification Screenshots Checklist for Submission

| No. | Screenshot Description | What to Capture |
|---|---|---|
| **1** | **GitHub Repository** | Repository root showing `backend/`, `frontend/`, `k8s/`, `Dockerfile`, and `Jenkinsfile`. |
| **2** | **AWS EC2 Console** | EC2 instances table showing instance `Running`, Public IP `13.220.184.51`, and security group. |
| **3** | **Jenkins Pipeline Dashboard** | Jenkins Stage View showing `specgen-ai-pipeline` with all stages **100% Green (SUCCESS)**. |
| **4** | **Docker Hub Repository** | Docker Hub web console at `zainuls/specgen-ai` displaying published tags (`latest`, `3`, `4`). |
| **5** | **Kubernetes Pods & Scaling** | Terminal output of `kubectl get pods,svc -o wide` displaying 4 running pods and NodePort `30080`. |
| **6** | **Live Application in Browser** | Browser window accessing `http://localhost:30080` showing the live SpecGen AI user interface. |
| **7** | **Code-Change Redeployment** | Browser or terminal output showing `/health` updated from version `1.0.0` to `2.0.0`. |

---

### 9. Viva Voce Preparation (Model Questions & Answers)

#### Questions from Experiment 4 (Microservices & Docker)
1. **What is a Microservice?**  
   *Answer:* A software architecture approach where an application is composed of small, independent services that communicate over lightweight protocols (such as HTTP REST APIs). Each service is independently deployable and scalable.
2. **What is Docker and how does it work?**  
   *Answer:* Docker is an open-source platform that uses OS-level virtualization (Linux cgroups and namespaces) to package an application and its dependencies into a portable, isolated container.
3. **What is the difference between a Docker Image and a Docker Container?**  
   *Answer:* A Docker Image is a read-only blueprint/template containing the application code, runtime, libraries, and instructions. A Docker Container is a live, runnable, stateful instance of that image with a read-write top layer.
4. **Why is a multi-stage Docker build used?**  
   *Answer:* Multi-stage builds allow using heavy build dependencies (like Node.js and compilers) in an initial stage, and copying only the final compiled static output into a clean, lightweight runtime stage (like Python slim). This drastically reduces image size, attack surface, and build time.

#### Questions from Experiment 5 (Jenkins CI/CD Pipeline)
5. **What is Continuous Integration (CI)?**  
   *Answer:* A development practice where developers frequently commit code changes into a shared repository, after which an automated server builds the code, runs automated test suites, and flags regressions immediately.
6. **What is Continuous Deployment / Delivery (CD)?**  
   *Answer:* Continuous Delivery ensures that every verified code change can be safely deployed to production at any time. Continuous Deployment automates this final step so every successful build automatically deploys to live environments without manual intervention.
7. **What is a Jenkinsfile?**  
   *Answer:* A text file that stores the complete CI/CD pipeline definition as code (Pipeline-as-Code). It defines the pipeline stages, environment variables, credentials, test scripts, and deployment steps in declarative or scripted Groovy syntax.
8. **Why are credentials stored in Jenkins rather than the repository?**  
   *Answer:* To uphold security best practices. Storing API tokens, Docker Hub passwords, or SSH keys in public or private Git repositories exposes credentials to unauthorized access. Jenkins encrypts credentials on disk and injects them only into memory during runtime steps.

#### Questions from Experiment 6 & CCA 2 (Kubernetes & Minikube)
9. **What is Kubernetes (K8s)?**  
   *Answer:* Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, load balancing, networking, and self-healing management of containerized workloads.
10. **What is a Kubernetes Pod?**  
    *Answer:* A Pod is the smallest deployable computing unit in Kubernetes. It encapsulates one or more closely coupled containers that share network namespaces (IP address) and storage volumes.
11. **What is a Deployment and what is its role?**  
    *Answer:* A Deployment is a Kubernetes controller that manages the declarative state of Pod replicas. It handles rolling updates, rollbacks to previous revisions, self-healing (recreating crashed pods), and dynamic horizontal scaling.
12. **What is a Kubernetes Service and why is NodePort used?**  
    *Answer:* A Service provides a stable, persistent virtual IP address and load balancer across a dynamic set of Pods whose IPs change upon recreation. A `NodePort` service exposes the application on a dedicated static port (range 30000–32767) on each cluster node so external clients can reach it.
13. **What is Minikube?**  
    *Answer:* Minikube is a lightweight Kubernetes distribution designed for local development and testing. It deploys a complete single-node Kubernetes cluster inside a container or VM on a local workstation.
14. **How does Kubernetes achieve zero downtime during a deployment update?**  
    *Answer:* Kubernetes uses a `RollingUpdate` deployment strategy governed by parameters such as `maxSurge` (how many pods can be created above the desired count) and `maxUnavailable` (how many pods can be unavailable). By starting new pods running the new image, waiting for their readiness probes to pass, and only then terminating old pods, user traffic is never dropped.
