.PHONY: up down quality test coverage migrate upgrade downgrade \
        kind-create kind-delete kind-load \
        k8s-build k8s-deploy k8s-delete k8s-status k8s-logs k8s-pf \
        validate validate-k8s validate-schema validate-sops validate-policies

# --load-restrictor=LoadRestrictionsNone is required because kustomize's
# configMapGenerator in base/monitoring references the dashboard JSON from
# the project's monitoring/ directory (outside the kustomize root).
KUST_FLAGS := --load-restrictor=LoadRestrictionsNone
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
# Kind (local cluster)
# ============================================

kind-create:
	kind create cluster --name todo-k8s

kind-delete:
	kind delete cluster --name todo-k8s

kind-load:
	kind load docker-image areebahmeddd/todo-api:1.0.0 --name todo-k8s

# ============================================
# Kubernetes (Kustomize)
# ============================================

k8s-build:
	docker build -t areebahmeddd/todo-api:1.0.0 .

k8s-deploy:
	kubectl apply -k k8s/argocd/

k8s-delete:
	kubectl delete -k k8s/argocd/

k8s-status:
	kubectl get all -n argocd
	kubectl get all -n todo-app
	kubectl get all -n monitoring
	kubectl get all -n traefik

k8s-logs:
	kubectl logs -n todo-app -l app.kubernetes.io/name=todo-api --tail=50 -f

k8s-pf:
	kubectl port-forward -n argocd svc/argocd-server 8080:443 &
	kubectl port-forward -n todo-app svc/todo-api 8000:8000 &
	kubectl port-forward -n monitoring svc/grafana 3000:3000 &
	kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
	kubectl port-forward -n traefik svc/traefik 9000:9000 &

# ============================================
# Validation
# ============================================

validate: validate-k8s validate-schema validate-sops validate-policies

validate-k8s:
	kustomize build $(KUST_FLAGS) k8s/overlays/dev | kubectl apply --dry-run=client -f -

validate-schema:
	kustomize build $(KUST_FLAGS) k8s/overlays/dev | \
	  kubeconform -strict -ignore-missing-schemas -summary -skip Secret -

validate-sops:
	@for f in k8s/overlays/dev/secrets/*.yaml k8s/overlays/prod/secrets/*.yaml; do \
		echo "Checking: $$f"; \
		if ! grep -q 'sops:' "$$f" || ! grep -q 'ENC\[' "$$f"; then \
			echo "ERROR: $$f is not SOPS-encrypted. Run: sops --encrypt --in-place $$f"; \
			exit 1; \
		fi; \
	 done; \
	 echo "All secrets are SOPS-encrypted."

validate-policies:
	kustomize build $(KUST_FLAGS) k8s/overlays/dev | conftest test --no-color --config-file .conftest.yaml --all-namespaces -
