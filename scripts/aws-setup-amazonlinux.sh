#!/bin/bash
# ==============================================================================
# CCA 2 - Automated AWS EC2 Setup Script for Amazon Linux 2023 / AL2
# Installs Java 17, Jenkins, Docker, Minikube, and kubectl
# ==============================================================================

set -e

echo ">>> [1/7] Updating system packages (dnf)..."
sudo dnf update -y
sudo dnf install -y wget curl git conntrack-tools iptables

echo ">>> [2/7] Installing Java 17 (Amazon Corretto) & Python 3..."
sudo dnf install -y java-17-amazon-corretto java-17-amazon-corretto-devel python3 python3-pip
java -version

echo ">>> [3/7] Installing Docker Engine..."
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker

# Add ec2-user to docker group
sudo usermod -aG docker ec2-user

echo ">>> [4/7] Installing Jenkins..."
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

sudo dnf upgrade -y
sudo dnf install -y jenkins
sudo systemctl enable jenkins
sudo systemctl start jenkins

# Add jenkins user to docker group
sudo usermod -aG docker jenkins

echo ">>> [5/7] Installing kubectl..."
KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm -f kubectl
kubectl version --client

echo ">>> [6/7] Installing Minikube..."
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm -f minikube-linux-amd64
minikube version

echo ">>> [7/7] Restarting services to apply group changes..."
sudo systemctl restart docker
sudo systemctl restart jenkins

echo ""
echo "=========================================================================="
echo "Installation complete!"
echo "Jenkins is running at: http://<EC2-PUBLIC-IP>:8080"
echo "To retrieve initial Jenkins admin password, run:"
echo "   sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
echo ""
echo "To start Minikube (run as standard ec2-user, NOT root):"
echo "   minikube start --driver=docker"
echo ""
echo "To allow Jenkins to access Minikube's kubectl config:"
echo "   sudo mkdir -p /var/lib/jenkins/.kube /var/lib/jenkins/.minikube"
echo "   sudo cp -r ~/.kube/config /var/lib/jenkins/.kube/"
echo "   sudo cp -r ~/.minikube/* /var/lib/jenkins/.minikube/ 2>/dev/null || true"
echo "   sudo chown -R jenkins:jenkins /var/lib/jenkins/.kube /var/lib/jenkins/.minikube"
echo "=========================================================================="
