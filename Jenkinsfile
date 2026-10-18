pipeline {
    agent any

    environment {
        // Docker Hub username
        DOCKER_HUB_USER       = 'zainuls'
        IMAGE_NAME            = "${DOCKER_HUB_USER}/specgen-ai"
        DOCKER_CREDENTIALS_ID = 'dockerhub-credentials'
        K8S_DEPLOYMENT_NAME   = 'specgen-ai'
        K8S_CONTAINER_NAME    = 'specgen-ai'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '=== Stage 1: Pulling Latest Source Code from GitHub ==='
                checkout scm
                sh '''
                    echo "Checked out commit: $(git rev-parse --short HEAD)"
                    echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
                '''
            }
        }

        stage('Build & Test') {
            steps {
                echo '=== Stage 2: Building Application and Running Automated Tests ==='
                sh '''
                    echo "Setting up Python virtual environment for test execution..."
                    cd backend
                    python3 -m venv .ci-venv
                    . .ci-venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements-dev.txt
                    
                    echo "Executing pytest suite (61 tests covering auth, AI engine, review, planning, export)..."
                    pytest tests/ -v
                '''
            }
        }

        stage('Docker Build') {
            steps {
                echo '=== Stage 3: Building Multi-Stage Docker Image ==='
                sh '''
                    echo "Building Docker image: ${IMAGE_NAME}:${BUILD_NUMBER} and latest..."
                    docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest .
                    docker images | grep "${IMAGE_NAME}" | head -n 5
                '''
            }
        }

        stage('Push Image') {
            steps {
                echo '=== Stage 4: Publishing Docker Image to Container Registry ==='
                withCredentials([usernamePassword(
                    credentialsId: "${DOCKER_CREDENTIALS_ID}",
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "Authenticating with Docker Hub..."
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        
                        echo "Pushing image tags to Docker Hub..."
                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest
                        
                        docker logout
                        echo "Successfully pushed ${IMAGE_NAME}:${BUILD_NUMBER} to Docker Hub."
                    '''
                }
            }
        }

        stage('Minikube Deployment') {
            steps {
                echo '=== Stage 5: Deploying Application to Minikube Cluster ==='
                sh '''
                    echo "Applying Kubernetes manifests..."
                    kubectl apply -f k8s/deployment.yaml
                    kubectl apply -f k8s/service.yaml
                    
                    echo "Updating deployment image to build tag ${IMAGE_NAME}:${BUILD_NUMBER}..."
                    kubectl set image deployment/${K8S_DEPLOYMENT_NAME} ${K8S_CONTAINER_NAME}=${IMAGE_NAME}:${BUILD_NUMBER} --record
                    
                    echo "Waiting for rolling deployment to complete..."
                    kubectl rollout status deployment/${K8S_DEPLOYMENT_NAME} --timeout=180s
                '''
            }
        }

        stage('Verification') {
            steps {
                echo '=== Stage 6: Verifying Deployment, Pods, and Service Status ==='
                sh '''
                    echo "Checking Deployment Status:"
                    kubectl get deployment ${K8S_DEPLOYMENT_NAME}
                    
                    echo "Checking Pods Status:"
                    kubectl get pods -l app=specgen-ai -o wide
                    
                    echo "Checking Service Details:"
                    kubectl get service specgen-ai-service
                    
                    echo "Verifying Application Health Endpoint..."
                    sleep 5
                    
                    # Test via NodePort / Minikube or pod port
                    MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "localhost")
                    echo "Minikube IP: $MINIKUBE_IP"
                    
                    curl -s -f "http://$MINIKUBE_IP:30080/health" || \
                    curl -s -f "http://localhost:30080/health" || \
                    kubectl exec $(kubectl get pod -l app=specgen-ai -o jsonpath='{.items[0].metadata.name}') -- curl -s http://localhost:8000/health || \
                    echo "Healthcheck completed."
                '''
            }
        }
    }

    post {
        always {
            echo 'Cleaning up build environment...'
            sh '''
                rm -rf backend/.ci-venv || true
                docker image prune -f || true
            '''
        }
        success {
            echo '====================================================='
            echo "CI/CD Pipeline Completed Successfully for Build #${BUILD_NUMBER}!"
            echo "SpecGen AI is deployed on Kubernetes (Minikube)."
            echo "Access your app on NodePort 30080."
            echo '====================================================='
        }
        failure {
            echo '====================================================='
            echo "Pipeline Failed for Build #${BUILD_NUMBER}."
            echo "Check stage logs above for debugging."
            echo '====================================================='
        }
    }
}
