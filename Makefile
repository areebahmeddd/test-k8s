SHELL := /bin/bash

.PHONY: up down quality test coverage migrate upgrade downgrade \
        minikube-create minikube-delete minikube-load minikube-tunnel \
        k8s-build k8s-deploy k8s-delete k8s-status k8s-logs k8s-pf \
        check-sops sops-encrypt sops-decrypt \
        validate validate-k8s validate-schema validate-sops validate-policies

# AGE private key used by SOPS — expected at the project root as age.key.
export SOPS_AGE_KEY_FILE := $(CURDIR)/age.key

OVERLAY ?= dev

# ============================================
# Development
# ============================================

up:
	docker compose up -d

down:
	docker compose down

# ============================================
# Code Quality
# ============================================

quality:
	uv run pre-commit run --all-files

# ============================================
# Code Testing
# ============================================

test:
	uv run pytest -v --cov=app --cov-report=term-missing

coverage:
	uv run pytest -v --cov=app --cov-report=term-missing --cov-report=html

# ============================================
# Database Migrations
# ============================================

migrate:
	uv run alembic revision --autogenerate -m "$(msg)"

upgrade:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade -1

# ============================================
# Minikube (local cluster)
# ============================================

minikube-create:
	minikube start --cpus=4 --memory=8192

minikube-delete:
	minikube delete

minikube-load:
	minikube image load areebahmeddd/todo-api:1.0.0
	minikube image load postgres:18-alpine
	minikube image load traefik:v3.6
	minikube image load grafana/grafana:12.4.0
	minikube image load grafana/loki:3.5.0
	minikube image load grafana/promtail:3.5.0
	minikube image load grafana/tempo:2.8.0
	minikube image load prom/prometheus:v3.10.0
	minikube image load prom/alertmanager:v0.31.0
	minikube image load otel/opentelemetry-collector-contrib:0.147.0

minikube-tunnel:
	minikube tunnel

# ============================================
# Kubernetes (Kustomize)
# ============================================

k8s-build:
	docker build -t areebahmeddd/todo-api:1.0.0 .

k8s-deploy: check-sops
	# Step 1: Apply ArgoCD (two passes — first installs CRDs, second applies Applications)
	kubectl apply -k k8s/argocd/ --server-side || kubectl apply -k k8s/argocd/ --server-side
	# Step 2: Apply the overlay manifests (namespaces, deployments, configmaps, ingress)
	kustomize build k8s/overlays/$(OVERLAY)/ | kubectl apply -f -
	# Step 3: Decrypt and apply SOPS-encrypted secrets
	@for f in k8s/overlays/$(OVERLAY)/secrets/*.yaml; do \
		echo "Applying secret: $$f"; \
		sops -d $$f | kubectl apply -f -; \
	 done

k8s-delete:
	kubectl delete -k k8s/argocd/ --ignore-not-found
	kustomize build k8s/overlays/$(OVERLAY)/ | kubectl delete -f - --ignore-not-found

k8s-status:
	kubectl get all -n argocd
	kubectl get all -n todo-app
	kubectl get all -n monitoring
	kubectl get all -n traefik

k8s-logs:
	kubectl logs -n todo-app -l app.kubernetes.io/name=todo-api --tail=50 -f

k8s-pf:
	kubectl port-forward -n argocd svc/argocd-server 8080:80 &
	kubectl port-forward -n todo-app svc/todo-api 8000:8000 &
	kubectl port-forward -n monitoring svc/grafana 3000:3000 &
	kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
	kubectl port-forward -n traefik svc/traefik 9000:9000 &

# ============================================
# SOPS Secret Management
# ============================================

# Guard: verify age.key exists and can decrypt the overlay secrets before touching the cluster.
# Three outcomes:
#   1. age.key missing           → hard stop  (get from team OR generate fresh)
#   2. age.key is the wrong key  → hard stop  (get team key OR edit plaintext + make sops-encrypt)
#   3. secrets are plaintext     → soft warn  (run make sops-encrypt before committing)
check-sops:
	@if [ ! -f "$(CURDIR)/age.key" ]; then \
		printf "\nERROR: age.key not found at $(CURDIR)/age.key\n\n"; \
		printf "  Team setup  — get from your team's secure channel (1Password / Vault / etc.)\n"; \
		printf "  Fresh setup — generate one: age-keygen -o age.key\n"; \
		printf "                then edit k8s/overlays/$(OVERLAY)/secrets/ with plaintext values\n"; \
		printf "                and run: make sops-encrypt\n\n"; \
		exit 1; \
	fi
	@probe=$$(ls k8s/overlays/$(OVERLAY)/secrets/*.yaml 2>/dev/null | head -1); \
	if [ -z "$$probe" ]; then exit 0; fi; \
	if grep -q 'ENC\[' "$$probe" 2>/dev/null; then \
		if ! sops -d "$$probe" > /dev/null 2>&1; then \
			printf "\nERROR: age.key cannot decrypt secrets in k8s/overlays/$(OVERLAY)/secrets/\n\n"; \
			printf "  Your key is different from the one used to encrypt these files.\n\n"; \
			printf "  Team setup  — replace age.key with the key from your team's secure channel\n"; \
			printf "  Fresh setup — replace each file in k8s/overlays/$(OVERLAY)/secrets/ with\n"; \
			printf "                plaintext values, then re-encrypt: make sops-encrypt\n\n"; \
			exit 1; \
		fi; \
	else \
		printf "WARNING: secrets in k8s/overlays/$(OVERLAY)/secrets/ are NOT encrypted.\n"; \
		printf "         Run 'make sops-encrypt' before committing.\n"; \
	fi

sops-encrypt:
	@for f in k8s/overlays/dev/secrets/*.yaml k8s/overlays/prod/secrets/*.yaml; do \
		echo "Encrypting: $$f"; \
		sops --encrypt --in-place $$f; \
	 done

sops-decrypt:
	@for f in k8s/overlays/dev/secrets/*.yaml k8s/overlays/prod/secrets/*.yaml; do \
		echo "Decrypting: $$f"; \
		sops --decrypt --in-place $$f; \
	 done

# ============================================
# Validation
# ============================================

validate: validate-k8s validate-schema validate-sops validate-policies

validate-k8s:
	kustomize build k8s/overlays/dev > /dev/null
	kustomize build k8s/overlays/prod > /dev/null

validate-schema:
	kustomize build k8s/overlays/dev | \
	  kubeconform -strict -ignore-missing-schemas -summary -skip Secret -

validate-sops:
	@for f in k8s/overlays/dev/secrets/*.yaml k8s/overlays/prod/secrets/*.yaml; do \
		echo "Checking: $$f"; \
		if ! grep -q 'sops:' "$$f" || ! grep -q 'ENC\[' "$$f"; then \
			echo "ERROR: $$f is not SOPS-encrypted."; \
			exit 1; \
		fi; \
	 done; \
	 echo "All secrets are SOPS-encrypted."

validate-policies:
	kustomize build k8s/overlays/dev | conftest test --no-color --config-file .conftest.yaml --all-namespaces -
