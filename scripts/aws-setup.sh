#!/bin/bash
# ==============================================================================
# CCA 2 - Automated AWS EC2 Setup Script
# Installs Java 17, Jenkins, Docker, Minikube, and kubectl on Ubuntu 22.04/24.04 LTS
# ==============================================================================

set -e

echo ">>> [1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y curl wget apt-transport-https ca-certificates gnupg lsb-release git conntrack

echo ">>> [2/7] Installing Java 17 (Required for Jenkins)..."
sudo apt-get install -y openjdk-17-jdk python3 python3-pip python3-venv
java -version

echo ">>> [3/7] Installing Docker Engine..."
sudo apt-get install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker

# Add ubuntu user to docker group
sudo usermod -aG docker $USER

echo ">>> [4/7] Installing Jenkins..."
sudo wget -O /usr/share/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" | sudo tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y jenkins
sudo systemctl enable jenkins
sudo systemctl start jenkins

# Add jenkins user to docker group so Jenkins can run docker commands
sudo usermod -aG docker jenkins

echo ">>> [5/7] Installing kubectl..."
KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl
kubectl version --client

echo ">>> [6/7] Installing Minikube..."
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64
minikube version

echo ">>> [7/7] Configuring Jenkins permissions for kubectl and Minikube..."
# Restart Jenkins and Docker to apply group changes
sudo systemctl restart docker
sudo systemctl restart jenkins

echo ""
echo "=========================================================================="
echo "Installation complete!"
echo "Jenkins is running at: http://<EC2-PUBLIC-IP>:8080"
echo "To retrieve initial Jenkins admin password, run:"
echo "   sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
echo ""
echo "To start Minikube (run as standard ubuntu user, NOT root):"
echo "   minikube start --driver=docker"
echo ""
echo "To allow Jenkins to access Minikube's kubectl config:"
echo "   sudo mkdir -p /var/lib/jenkins/.kube /var/lib/jenkins/.minikube"
echo "   sudo cp -r ~/.kube/config /var/lib/jenkins/.kube/"
echo "   sudo cp -r ~/.minikube/* /var/lib/jenkins/.minikube/ 2>/dev/null || true"
echo "   sudo chown -R jenkins:jenkins /var/lib/jenkins/.kube /var/lib/jenkins/.minikube"
echo "=========================================================================="
