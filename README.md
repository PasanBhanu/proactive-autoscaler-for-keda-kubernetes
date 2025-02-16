# KEDA External Scaler for Predictive Scaling using LSTM and FB Prophet

## Prerequisites

- Docker
- Kubernetes
- KEDA

## Install KEDA

```bash
kubectl create namespace keda
helm upgrade --install keda kedacore/keda --values keda-values.yaml --namespace keda
```

## Build the Docker Image

```bash
docker build -t pasanbhanu/keda-lsfb-scaler:latest .
docker push pasanbhanu/keda-lsfb-scaler:latest
```

## Deploy the Docker Image to the Kubernetes Cluster

```bash
kubectl apply -f kubernetes/deployment.yaml
```


## Deploy the KEDA Scaler to the Kubernetes Cluster

```bash
kubectl apply -f kubernetes/lsfb-scaler.yaml
```


