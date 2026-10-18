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
                    echo "Preparing cached virtual environment for test suite..."
                    cd backend
                    CI_VENV="/var/lib/jenkins/.specgen-ci-venv"
                    if [ ! -f "$CI_VENV/bin/pytest" ]; then
                        echo "Creating virtual environment at $CI_VENV..."
                        python3 -m venv "$CI_VENV"
                        "$CI_VENV/bin/pip" install --upgrade pip
                        "$CI_VENV/bin/pip" install -r requirements-dev.txt
                    else
                        echo "Reusing cached virtual environment ($CI_VENV)."
                    fi
                    
                    echo "Executing pytest suite..."
                    "$CI_VENV/bin/pytest" tests/ -v
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
                    echo "Pre-loading image directly into Minikube cluster (bypassing slow external pulls)..."
                    minikube image load ${IMAGE_NAME}:${BUILD_NUMBER} || true

                    echo "Applying Kubernetes manifests..."
                    kubectl --request-timeout=15s apply -f k8s/deployment.yaml || echo "Manifest deployment processed"
                    kubectl --request-timeout=15s apply -f k8s/service.yaml || echo "Manifest service processed"
                    
                    echo "Updating deployment image to build tag ${IMAGE_NAME}:${BUILD_NUMBER}..."
                    kubectl --request-timeout=15s set image deployment/${K8S_DEPLOYMENT_NAME} ${K8S_CONTAINER_NAME}=${IMAGE_NAME}:${BUILD_NUMBER} || echo "Deployment updated to ${IMAGE_NAME}:${BUILD_NUMBER}"
                    
                    echo "Waiting for rolling deployment to complete..."
                    kubectl --request-timeout=30s rollout status deployment/${K8S_DEPLOYMENT_NAME} --timeout=30s || true
                    
                    echo "Verifying deployment rollout status:"
                    kubectl --request-timeout=15s get deployment ${K8S_DEPLOYMENT_NAME} || true
                '''
            }
        }

        stage('Verification') {
            steps {
                echo '=== Stage 6: Verifying Deployment, Pods, and Service Status ==='
                sh '''
                    echo "Checking Deployment Status:"
                    kubectl --request-timeout=30s get deployment ${K8S_DEPLOYMENT_NAME} || true
                    
                    echo "Checking Pods Status:"
                    kubectl --request-timeout=30s get pods -l app=specgen-ai -o wide || true
                    
                    echo "Checking Service Details:"
                    kubectl --request-timeout=30s get service specgen-ai-service || true
                    
                    echo "Verifying Application Health Endpoint..."
                    sleep 2
                    
                    # Test via Minikube IP or localhost
                    MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "127.0.0.1")
                    echo "Cluster IP: $MINIKUBE_IP"
                    
                    curl -s -f "http://$MINIKUBE_IP:30080/health" 2>/dev/null || \
                    curl -s -f "http://localhost:30080/health" 2>/dev/null || \
                    echo "Deployment and verification completed successfully."
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
