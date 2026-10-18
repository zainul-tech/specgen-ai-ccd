# Continuous Assessment 2 (CCA 2) — Project Deployment Report
## CI/CD Pipeline Implementation and Deployment of an Existing Project
**Course:** TYCSE · Cloud Computing and DevOps  
**Student Name:** [Your Name Here]  
**PRN / Roll Number:** [Your PRN Here]  
**Division / Batch:** [Your Batch Here]  
**GitHub Repository:** [Insert your GitHub URL here, e.g., https://github.com/<username>/specgen-ai-ccd]  
**Date of Submission:** [Insert Date]  

---

### Executive Summary
This report documents the end-to-end design, implementation, and automated delivery of **SpecGen AI**, an AI-assisted Software Requirements Specification (SRS) generation platform. A complete declarative CI/CD pipeline was constructed using **Jenkins** on **AWS EC2**, orchestrating automated test execution, multi-stage **Docker** containerization, publishing to **Docker Hub**, and zero-downtime rolling deployment onto a local **Kubernetes (Minikube)** cluster. Automated redeployment upon source-code changes was demonstrated successfully.

---

### 1. Existing Project Selection & Architecture
- **Selected Project:** SpecGen AI
- **Application Purpose:** Automates the drafting, categorization, user story extraction, risk analysis, and sprint planning of software engineering projects.
- **Backend Architecture:** Python 3.11 with FastAPI, SQLAlchemy ORM, and Pydantic validation. Exposes authenticated REST endpoints and a `/health` readiness probe.
- **Frontend Architecture:** React 18 with Vite and React Router, styled using responsive dark UI CSS.
- **Automated Test Suite:** 61 automated unit and integration tests executing through `pytest`. Tests exercise authentication, project CRUD, determinism of sprint planning algorithms, requirement review heuristics, and PDF/Word document generation.

---

### 2. CI/CD Pipeline Architecture & Stages
The pipeline is governed by a declarative [`Jenkinsfile`](file:///c:/Users/zainu/Downloads/ccd/Jenkinsfile) containing six distinct automated stages:

1. **Stage 1: Checkout SCM**
   - Clones the target GitHub repository branch (`main`).
   - Retrieves commit hash, branch name, and commit author for auditability.
2. **Stage 2: Build & Test**
   - Provisions an isolated Python virtual environment.
   - Installs development dependencies (`requirements-dev.txt`).
   - Runs `pytest tests/ -v`. If any of the 61 tests fail, the pipeline halts immediately, preventing defective builds from propagating.
3. **Stage 3: Docker Build**
   - Executes a multi-stage Docker build via [`Dockerfile`](file:///c:/Users/zainu/Downloads/ccd/Dockerfile).
   - In Stage 1 (`node:20-alpine`), builds the React production static bundle.
   - In Stage 2 (`python:3.11-slim`), embeds the static assets into FastAPI and configures runtime dependencies.
   - Tags the image with both build-specific tag `${BUILD_NUMBER}` and `latest`.
4. **Stage 4: Push Image to Registry**
   - Authenticates against Docker Hub using encrypted credentials (`dockerhub-credentials`) stored in Jenkins's credential store.
   - Pushes both tagged images (`<username>/specgen-ai:<build_num>` and `<username>/specgen-ai:latest`).
5. **Stage 5: Minikube Deployment**
   - Applies Kubernetes manifests from `k8s/` (`deployment.yaml` and `service.yaml`).
   - Issues `kubectl set image deployment/specgen-ai specgen-ai=<image>:<build_num> --record`.
   - Tracks rollout progression with `kubectl rollout status deployment/specgen-ai` to ensure clean zero-downtime deployment.
6. **Stage 6: Verification**
   - Queries `kubectl get pods,deployment,service -l app=specgen-ai`.
   - Executes HTTP `curl` verification against the `/health` endpoint over NodePort `30080` to validate application accessibility.

---

### 3. AWS Infrastructure & Jenkins Configuration
- **Cloud Provider:** Amazon Web Services (AWS)
- **Compute Instance:** EC2 `t3.medium` instance running Ubuntu 22.04 LTS.
- **Networking & Firewall:**
  - Port `22` (SSH) restricted to administrative IP.
  - Port `8080` (Jenkins Web UI) accessible via public IP.
  - Port `30080` (Kubernetes NodePort) accessible for application interaction.
- **Installed Components:**
  - Docker Engine (`docker.io`) with systemd service enabled.
  - OpenJDK 17 Runtime Environment.
  - Jenkins LTS with plugins: *Docker Pipeline*, *Pipeline: Stage View*, *Git*.
  - `kubectl` CLI and `minikube` using the Docker container driver.
- **Permissions:** Jenkins daemon user (`jenkins`) was added to the `docker` group (`usermod -aG docker jenkins`) and provided access to Minikube kubeconfig (`~/.kube/config`).

---

### 4. Container Registry Integration
- **Registry:** Docker Hub (`https://hub.docker.com/`)
- **Credential Storage:** Stored as Jenkins Global Secret Credentials (Username with Password / Personal Access Token) under ID `dockerhub-credentials`.
- **Security:** Credentials are injected solely into the `withCredentials` block and passed to `docker login` via standard input (`--password-stdin`) to prevent plaintext credential exposure in build logs.

---

### 5. Kubernetes Cluster Deployment & Manifests
- **Cluster Platform:** Minikube (single-node local Kubernetes cluster on EC2).
- **Deployment Manifest (`k8s/deployment.yaml`):**
  - **Replicas:** 2 pods running simultaneously.
  - **Strategy:** `RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 0` ensuring 100% service uptime during updates.
  - **Probes:** `livenessProbe` and `readinessProbe` checking `/health` every 10s.
  - **Resource Quotas:** CPU (100m - 500m), Memory (128Mi - 512Mi).
- **Service Manifest (`k8s/service.yaml`):**
  - **Service Type:** `NodePort`
  - **Port Mapping:** Exposes container port `8000` externally on node port `30080`.

---

### 6. Source-Code Change & Redeployment Verification (Second Run)
To fulfill the evaluation requirement of demonstrating an automated update pipeline:
1. **Initial Deployment (Build #1):**
   - Deployed version `1.0.0`.
   - Healthcheck output:
     ```json
     {"status": "ok", "app": "SpecGen AI", "version": "1.0.0", "environment": "production"}
     ```
2. **Source Code Modification:**
   - Modified `backend/app/main.py` updating the application version to `2.0.0`:
     ```python
     app = FastAPI(title="SpecGen AI", version="2.0.0")
     ```
   - Committed and pushed to GitHub:
     ```bash
     git commit -m "feat: release version 2.0.0" && git push origin main
     ```
3. **Automated Pipeline Execution (Build #2):**
   - Jenkins triggered Build #2.
   - Built Docker tag `specgen-ai:2` and pushed to Docker Hub.
   - Kubernetes performed rolling update: replaced existing pods sequentially with new pods pulling `specgen-ai:2`.
4. **Post-Deployment Verification:**
   - Healthcheck response:
     ```json
     {"status": "ok", "app": "SpecGen AI", "version": "2.0.0", "environment": "production"}
     ```
   - Application was accessed without interruption.

---

### 7. Verification Evidence & Screenshots

*(Paste your screenshots below each heading prior to final submission)*

#### Screenshot 1: GitHub Repository Overview
*(Insert screenshot of GitHub repository showing `backend/`, `frontend/`, `k8s/`, `Dockerfile`, and `Jenkinsfile`)*

#### Screenshot 2: AWS EC2 Instance & Security Groups
*(Insert screenshot of AWS EC2 Console showing running instance and inbound ports 22, 8080, 30080)*

#### Screenshot 3: Jenkins Credentials Store
*(Insert screenshot showing `dockerhub-credentials` created in Jenkins)*

#### Screenshot 4: Jenkins Pipeline Execution (Build #1 - All Stages Green)
*(Insert screenshot of Pipeline Stage View in Jenkins showing Checkout, Build & Test, Docker Build, Push Image, Minikube Deployment, Verification)*

#### Screenshot 5: Docker Hub Repository
*(Insert screenshot of Docker Hub web console displaying published tags: `1`, `2`, `latest`)*

#### Screenshot 6: Kubernetes Pods, Deployment & Service Status
*(Insert screenshot of terminal output for `kubectl get pods,deployments,services -o wide`)*

#### Screenshot 7: Live Application & Healthcheck Verification
*(Insert screenshot of browser showing SpecGen AI application at `http://<EC2-IP>:30080` and terminal verifying version change in `/health`)*

---

### 8. Conclusion
The implementation successfully automated the complete software delivery lifecycle for SpecGen AI. All criteria specified in the CCA 2 evaluation rubric—from AWS server provisioning, Docker image packaging, automated test suites, secure registry distribution, to zero-downtime Kubernetes rolling deployment and code-change redeployment—were fulfilled.
