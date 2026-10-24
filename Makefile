SHELL := /bin/bash

OVERLAY ?= dev
IMAGE   := areebahmeddd/todo-api:1.1.0
SECRETS := $(wildcard k8s/overlays/$(OVERLAY)/secrets/*.yaml)
SCHEMAS := -schema-location default \
           -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

# SOPS reads the age private key from the project root.
export SOPS_AGE_KEY_FILE := $(CURDIR)/age.key

.PHONY: help up down lint test quality migration migrate downgrade \
        cluster-up cluster-down image image-push cnpg-operator \
        k8s-deploy k8s-secrets k8s-delete k8s-status check-sops sops-encrypt \
        pulumi-install pulumi-up pulumi-destroy \
        validate validate-k8s validate-schema validate-sops validate-policies

help: ## List targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

# Local development

up: ## Start the API + PostgreSQL with docker compose
	docker compose up -d --build

down: ## Stop docker compose and drop its volume
	docker compose down -v

lint: ## Lint and format with ruff
	uv run ruff check . --fix
	uv run ruff format .

test: ## Run the test suite with coverage
	uv run pytest -v --cov=app --cov-report=term-missing

quality: ## Run all pre-commit hooks against every file
	uv run pre-commit run --all-files

migration: ## Generate a migration: make migration msg="add column"
	uv run alembic revision --autogenerate -m "$(msg)"

migrate: ## Apply all migrations
	uv run alembic upgrade head

downgrade: ## Roll back the last migration
	uv run alembic downgrade -1

# Local cluster

cluster-up: ## Create the minikube cluster
	minikube start --cni=calico --memory=8192 --cpus=4
	kubectl rollout status daemonset/calico-node -n kube-system --timeout=300s

cluster-down: ## Delete the minikube cluster
	minikube delete

image: ## Build the API image inside minikube
	minikube image build -t $(IMAGE) -f Dockerfile .

image-push: ## Build and publish the API image to Docker Hub (needed by the GitOps path)
	docker build -t $(IMAGE) .
	docker push $(IMAGE)

cnpg-operator: ## Install the CloudNativePG operator unless already present (used by Tilt)
	kubectl get deploy -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg -o name 2>/dev/null | grep -q . || \
		helm upgrade --install cloudnative-pg oci://ghcr.io/cloudnative-pg/charts/cloudnative-pg \
			--version 0.29.1 --namespace cnpg-system --create-namespace --set replicaCount=1 \
			--set crds.create=$$(kubectl get crd clusters.postgresql.cnpg.io > /dev/null 2>&1 && echo false || echo true) \
			--wait

# GitOps deploy

k8s-deploy: check-sops ## Bootstrap ArgoCD + Applications, then apply secrets
	# The first apply creates the ArgoCD CRDs; Applications need them registered.
	kubectl apply --server-side -k k8s/argocd/$(OVERLAY) || { \
		kubectl wait --for=condition=Established crd/applications.argoproj.io --timeout=120s && \
		kubectl apply --server-side -k k8s/argocd/$(OVERLAY); }
	$(MAKE) k8s-secrets

k8s-secrets: check-sops ## Decrypt and apply the overlay secrets (plaintext never hits disk)
	kubectl apply -f k8s/base/app/namespace.yaml -f k8s/base/monitoring/namespace.yaml
	@for f in $(SECRETS); do echo "Applying $$f"; sops -d $$f | kubectl apply -f -; done

k8s-delete: ## Remove the Applications (ArgoCD prunes their resources), then ArgoCD
	kubectl delete -n argocd applications.argoproj.io --all --ignore-not-found --wait
	kubectl delete -k k8s/argocd/$(OVERLAY) --ignore-not-found

k8s-status: ## Show workloads, plus ArgoCD Applications and the database cluster when installed
	kubectl get pods -A -l 'app.kubernetes.io/part-of=todo-k8s'
	-kubectl get applications.argoproj.io -n argocd
	-kubectl get clusters.postgresql.cnpg.io -n todo-app

check-sops: ## Fail fast unless age.key exists and decrypts the overlay secrets
	@test -f age.key || { echo "age.key not found. Get the team key, or create one (age-keygen -o age.key), re-encrypt with 'make sops-encrypt' and update .sops.yaml."; exit 1; }
	@sops -d $(firstword $(SECRETS)) > /dev/null || { echo "age.key cannot decrypt k8s/overlays/$(OVERLAY)/secrets/."; exit 1; }

sops-encrypt: ## Encrypt any plaintext secret files in both overlays
	@for f in k8s/overlays/*/secrets/*.yaml; do \
		grep -q '^sops:' $$f && continue; echo "Encrypting $$f"; sops encrypt --in-place $$f; \
	done

# Pulumi

pulumi-install: ## Install the Pulumi program's dependencies (uv)
	cd infra && pulumi install

pulumi-up: ## Bootstrap ArgoCD + secrets for stack $(OVERLAY)
	cd infra && pulumi up --stack $(OVERLAY)

pulumi-destroy: ## Remove everything the Pulumi stack created
	# Delete the Applications first, while ArgoCD is still running to process their finalizers.
	kubectl delete -n argocd applications.argoproj.io --all --ignore-not-found --wait
	cd infra && pulumi destroy --stack $(OVERLAY)

# Validation

validate: validate-k8s validate-schema validate-sops validate-policies ## Run all checks

validate-k8s: ## Render every kustomization
	@for d in k8s/overlays/dev k8s/overlays/prod k8s/argocd/dev k8s/argocd/prod; do \
		echo "Building $$d"; kustomize build $$d > /dev/null || exit 1; done

validate-schema: ## Validate rendered overlays against Kubernetes and CRD schemas
	@for o in dev prod; do kustomize build k8s/overlays/$$o | \
		kubeconform -strict -summary -skip Secret $(SCHEMAS) - || exit 1; done

validate-sops: ## Ensure every committed secret is SOPS-encrypted
	@for f in k8s/overlays/*/secrets/*.yaml; do \
		grep -q '^sops:' $$f && grep -q 'ENC\[' $$f || { echo "$$f is not encrypted"; exit 1; }; \
	done; echo "All secrets are SOPS-encrypted."

validate-policies: ## Unit-test the OPA policies, then run them against both overlays
	@conftest verify && for o in dev prod; do kustomize build k8s/overlays/$$o | \
		conftest test --all-namespaces --fail-on-warn - || exit 1; done
