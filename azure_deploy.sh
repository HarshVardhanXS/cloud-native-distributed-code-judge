#!/bin/bash

# Azure end-to-end deployment script for Cloud-Native Code Judge
# Provisions: ACR, PostgreSQL Flexible Server, Azure Cache for Redis,
# optional Blob Storage, App Service (and optional Container Apps), then runs health checks.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_TEMPLATE_PATH="${SCRIPT_DIR}/.env.example"
GENERATED_ENV_PATH="${SCRIPT_DIR}/.env.azure.generated"

DEPLOY_CONTAINER_APPS="n"
ENABLE_BLOB_STORAGE="n"

print_header() {
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Cloud-Native Code Judge - Azure Deploy${NC}"
  echo -e "${GREEN}========================================${NC}"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo -e "${RED}Error: required command '$cmd' not found.${NC}"
    exit 1
  fi
}

check_prerequisites() {
  echo -e "\n${YELLOW}Checking prerequisites...${NC}"
  require_command az
  require_command docker
  require_command curl
  require_command openssl

  if [[ "$DEPLOY_CONTAINER_APPS" == "y" ]]; then
    az extension add --name containerapp --upgrade >/dev/null
  fi

  echo -e "${GREEN}? Prerequisites met${NC}"
}

ensure_env_template() {
  if [[ ! -f "$ENV_TEMPLATE_PATH" ]]; then
    cat > "$ENV_TEMPLATE_PATH" <<'EOF'
# Required by app runtime
DATABASE_URL=postgresql://username:password@hostname:5432/database?sslmode=require
REDIS_URL=rediss://:password@your-redis-host:6380/0
SECRET_KEY=replace-with-32-char-secret
AZURE_SUBSCRIPTION_ID=replace-with-subscription-id
AZURE_EXECUTION_RESOURCE_GROUP=replace-with-resource-group
AZURE_LOCATION=eastus

# Execution container image for ACI executor
AZURE_EXECUTION_IMAGE=replace-with-acr-image
AZURE_EXECUTION_REGISTRY_SERVER=replace-with-acr-server
AZURE_EXECUTION_REGISTRY_USERNAME=replace-with-acr-user
AZURE_EXECUTION_REGISTRY_PASSWORD=replace-with-acr-password
AZURE_EXECUTION_TIMEOUT_SECONDS=30
AZURE_EXECUTION_CPU=0.5
AZURE_EXECUTION_MEMORY_GB=1.0
AZURE_EXECUTION_POLL_INTERVAL_SECONDS=2

# Optional app settings
CORS_ORIGINS=http://localhost:3000
AZURE_BLOB_CONNECTION=
EOF
    echo -e "${GREEN}? Created .env.example template${NC}"
  fi
}

prompt_bool() {
  local prompt="$1"
  local default="$2"
  local value
  read -r -p "$prompt" value
  value="${value:-$default}"
  if [[ "$value" =~ ^[Yy]$ ]]; then
    echo "y"
  else
    echo "n"
  fi
}

get_config() {
  echo -e "\n${YELLOW}Configuration:${NC}"

  read -r -p "Azure subscription ID: " SUBSCRIPTION_ID
  read -r -p "Resource group name: " RESOURCE_GROUP
  read -r -p "Azure location (e.g., eastus): " LOCATION

  read -r -p "ACR name (lowercase, globally unique): " REGISTRY_NAME
  read -r -p "Image name [code-judge]: " IMAGE_NAME
  IMAGE_NAME="${IMAGE_NAME:-code-judge}"
  read -r -p "Image tag [latest]: " IMAGE_TAG
  IMAGE_TAG="${IMAGE_TAG:-latest}"

  read -r -p "App Service app name (globally unique): " APP_NAME
  read -r -p "App Service plan name [${RESOURCE_GROUP}-plan]: " PLAN_NAME
  PLAN_NAME="${PLAN_NAME:-${RESOURCE_GROUP}-plan}"

  read -r -p "PostgreSQL server name (globally unique): " POSTGRES_SERVER_NAME
  read -r -p "PostgreSQL database name [codejudge]: " POSTGRES_DB_NAME
  POSTGRES_DB_NAME="${POSTGRES_DB_NAME:-codejudge}"
  read -r -p "PostgreSQL admin username [judgeadmin]: " POSTGRES_ADMIN_USER
  POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-judgeadmin}"
  read -r -s -p "PostgreSQL admin password: " POSTGRES_ADMIN_PASSWORD
  echo

  read -r -p "Redis cache name (globally unique): " REDIS_NAME

  DEPLOY_CONTAINER_APPS="$(prompt_bool 'Deploy Azure Container Apps too? (y/N): ' 'n')"
  if [[ "$DEPLOY_CONTAINER_APPS" == "y" ]]; then
    read -r -p "Container Apps environment name [${RESOURCE_GROUP}-cae]: " CONTAINERAPP_ENV_NAME
    CONTAINERAPP_ENV_NAME="${CONTAINERAPP_ENV_NAME:-${RESOURCE_GROUP}-cae}"
    read -r -p "Container App name [${APP_NAME}-ca]: " CONTAINERAPP_NAME
    CONTAINERAPP_NAME="${CONTAINERAPP_NAME:-${APP_NAME}-ca}"
  fi

  ENABLE_BLOB_STORAGE="$(prompt_bool 'Create Blob Storage and set AZURE_BLOB_CONNECTION? (y/N): ' 'n')"
  if [[ "$ENABLE_BLOB_STORAGE" == "y" ]]; then
    read -r -p "Storage account name (lowercase, globally unique): " STORAGE_ACCOUNT
    read -r -p "Blob container name [artifacts]: " BLOB_CONTAINER_NAME
    BLOB_CONTAINER_NAME="${BLOB_CONTAINER_NAME:-artifacts}"
  fi

  SECRET_KEY="$(openssl rand -hex 32)"

  REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"
  FULL_IMAGE_NAME="${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"

  echo -e "\n${YELLOW}Configuration Summary:${NC}"
  echo "Subscription: ${SUBSCRIPTION_ID}"
  echo "Resource Group: ${RESOURCE_GROUP}"
  echo "Location: ${LOCATION}"
  echo "ACR Image: ${FULL_IMAGE_NAME}"
  echo "App Service: ${APP_NAME}"
  echo "PostgreSQL: ${POSTGRES_SERVER_NAME}/${POSTGRES_DB_NAME}"
  echo "Redis: ${REDIS_NAME}"
  echo "Container Apps: ${DEPLOY_CONTAINER_APPS}"
  echo "Blob Storage: ${ENABLE_BLOB_STORAGE}"
}

login_azure() {
  echo -e "\n${YELLOW}Logging in to Azure...${NC}"
  az login >/dev/null
  az account set --subscription "$SUBSCRIPTION_ID"
  echo -e "${GREEN}? Logged in to Azure${NC}"
}

create_resource_group() {
  echo -e "\n${YELLOW}Creating resource group...${NC}"
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null
  echo -e "${GREEN}? Resource group ready${NC}"
}

create_container_registry() {
  echo -e "\n${YELLOW}Creating Azure Container Registry...${NC}"
  az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$REGISTRY_NAME" \
    --sku Basic \
    --admin-enabled true >/dev/null

  REGISTRY_USERNAME="$(az acr credential show --resource-group "$RESOURCE_GROUP" --name "$REGISTRY_NAME" --query username -o tsv)"
  REGISTRY_PASSWORD="$(az acr credential show --resource-group "$RESOURCE_GROUP" --name "$REGISTRY_NAME" --query passwords[0].value -o tsv)"

  echo -e "${GREEN}? ACR ready${NC}"
}

build_and_push_image() {
  echo -e "\n${YELLOW}Building and pushing image to ACR...${NC}"
  echo "$REGISTRY_PASSWORD" | docker login -u "$REGISTRY_USERNAME" --password-stdin "$REGISTRY_URL" >/dev/null
  docker build -t "$FULL_IMAGE_NAME" .
  docker push "$FULL_IMAGE_NAME"
  echo -e "${GREEN}? Image pushed: ${FULL_IMAGE_NAME}${NC}"
}

create_postgres() {
  echo -e "\n${YELLOW}Creating Azure Database for PostgreSQL Flexible Server...${NC}"
  az postgres flexible-server create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER_NAME" \
    --location "$LOCATION" \
    --admin-user "$POSTGRES_ADMIN_USER" \
    --admin-password "$POSTGRES_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --version 16 \
    --storage-size 32 \
    --public-access 0.0.0.0 >/dev/null

  az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --database-name "$POSTGRES_DB_NAME" >/dev/null

  az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER_NAME" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 >/dev/null

  POSTGRES_HOST="$(az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_SERVER_NAME" --query fullyQualifiedDomainName -o tsv)"
  DATABASE_URL="postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB_NAME}?sslmode=require"

  echo -e "${GREEN}? PostgreSQL ready${NC}"
}

create_redis() {
  echo -e "\n${YELLOW}Creating Azure Cache for Redis...${NC}"
  az redis create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$REDIS_NAME" \
    --location "$LOCATION" \
    --sku Basic \
    --vm-size C0 \
    --enable-non-ssl-port false >/dev/null

  REDIS_KEY="$(az redis list-keys --resource-group "$RESOURCE_GROUP" --name "$REDIS_NAME" --query primaryKey -o tsv)"
  REDIS_HOST="${REDIS_NAME}.redis.cache.windows.net"
  REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_HOST}:6380/0"

  echo -e "${GREEN}? Redis ready${NC}"
}

create_blob_storage_optional() {
  AZURE_BLOB_CONNECTION=""
  if [[ "$ENABLE_BLOB_STORAGE" != "y" ]]; then
    return
  fi

  echo -e "\n${YELLOW}Creating Azure Blob Storage...${NC}"
  az storage account create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$STORAGE_ACCOUNT" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 >/dev/null

  az storage container create \
    --account-name "$STORAGE_ACCOUNT" \
    --name "$BLOB_CONTAINER_NAME" \
    --auth-mode login >/dev/null

  AZURE_BLOB_CONNECTION="$(az storage account show-connection-string --resource-group "$RESOURCE_GROUP" --name "$STORAGE_ACCOUNT" --query connectionString -o tsv)"

  echo -e "${GREEN}? Blob Storage ready${NC}"
}

configure_runtime_env_values() {
  AZURE_EXECUTION_IMAGE="${FULL_IMAGE_NAME}"
  AZURE_EXECUTION_REGISTRY_SERVER="$REGISTRY_URL"
  AZURE_EXECUTION_REGISTRY_USERNAME="$REGISTRY_USERNAME"
  AZURE_EXECUTION_REGISTRY_PASSWORD="$REGISTRY_PASSWORD"

  APP_SETTINGS=(
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE=false"
    "WEBSITES_PORT=8000"
    "SECRET_KEY=${SECRET_KEY}"
    "DATABASE_URL=${DATABASE_URL}"
    "REDIS_URL=${REDIS_URL}"
    "AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}"
    "AZURE_EXECUTION_RESOURCE_GROUP=${RESOURCE_GROUP}"
    "AZURE_LOCATION=${LOCATION}"
    "AZURE_EXECUTION_IMAGE=${AZURE_EXECUTION_IMAGE}"
    "AZURE_EXECUTION_REGISTRY_SERVER=${AZURE_EXECUTION_REGISTRY_SERVER}"
    "AZURE_EXECUTION_REGISTRY_USERNAME=${AZURE_EXECUTION_REGISTRY_USERNAME}"
    "AZURE_EXECUTION_REGISTRY_PASSWORD=${AZURE_EXECUTION_REGISTRY_PASSWORD}"
    "AZURE_EXECUTION_TIMEOUT_SECONDS=30"
    "AZURE_EXECUTION_CPU=0.5"
    "AZURE_EXECUTION_MEMORY_GB=1.0"
    "AZURE_EXECUTION_POLL_INTERVAL_SECONDS=2"
    "CORS_ORIGINS=http://localhost:3000"
  )

  if [[ -n "$AZURE_BLOB_CONNECTION" ]]; then
    APP_SETTINGS+=("AZURE_BLOB_CONNECTION=${AZURE_BLOB_CONNECTION}")
  fi
}

create_app_service_plan() {
  echo -e "\n${YELLOW}Creating App Service plan...${NC}"
  az appservice plan create \
    --name "$PLAN_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --sku B1 \
    --is-linux >/dev/null
  echo -e "${GREEN}? App Service plan ready${NC}"
}

deploy_app_service() {
  echo -e "\n${YELLOW}Deploying App Service from ACR image...${NC}"

  az webapp create \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$PLAN_NAME" \
    --name "$APP_NAME" \
    --deployment-container-image-name "$FULL_IMAGE_NAME" >/dev/null

  az webapp config container set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --docker-custom-image-name "$FULL_IMAGE_NAME" \
    --docker-registry-server-url "https://${REGISTRY_URL}" \
    --docker-registry-server-user "$REGISTRY_USERNAME" \
    --docker-registry-server-password "$REGISTRY_PASSWORD" >/dev/null

  az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --settings "${APP_SETTINGS[@]}" >/dev/null

  APP_SERVICE_URL="https://${APP_NAME}.azurewebsites.net"
  echo -e "${GREEN}? App Service deployed: ${APP_SERVICE_URL}${NC}"
}

deploy_container_apps_optional() {
  if [[ "$DEPLOY_CONTAINER_APPS" != "y" ]]; then
    return
  fi

  echo -e "\n${YELLOW}Deploying Azure Container Apps from ACR image...${NC}"

  az containerapp env create \
    --name "$CONTAINERAPP_ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" >/dev/null

  az containerapp create \
    --name "$CONTAINERAPP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINERAPP_ENV_NAME" \
    --image "$FULL_IMAGE_NAME" \
    --target-port 8000 \
    --ingress external \
    --registry-server "$REGISTRY_URL" \
    --registry-username "$REGISTRY_USERNAME" \
    --registry-password "$REGISTRY_PASSWORD" \
    --cpu 0.5 \
    --memory 1.0Gi \
    --env-vars "${APP_SETTINGS[@]}" >/dev/null

  CONTAINER_APP_FQDN="$(az containerapp show --name "$CONTAINERAPP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)"
  CONTAINER_APP_URL="https://${CONTAINER_APP_FQDN}"
  echo -e "${GREEN}? Container App deployed: ${CONTAINER_APP_URL}${NC}"
}

health_check_url() {
  local target_url="$1"
  local retries="${2:-30}"
  local sleep_seconds="${3:-10}"

  echo -e "\n${YELLOW}Health check: ${target_url}/health${NC}"
  for ((i=1; i<=retries; i++)); do
    if curl -fsS "${target_url}/health" >/dev/null; then
      echo -e "${GREEN}? Health check passed for ${target_url}${NC}"
      return 0
    fi
    echo "Attempt ${i}/${retries} failed; retrying in ${sleep_seconds}s..."
    sleep "$sleep_seconds"
  done

  echo -e "${RED}Health check failed for ${target_url}${NC}"
  return 1
}

write_generated_env_file() {
  cat > "$GENERATED_ENV_PATH" <<EOF
# Generated by azure_deploy.sh
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}
SECRET_KEY=${SECRET_KEY}
AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}
AZURE_EXECUTION_RESOURCE_GROUP=${RESOURCE_GROUP}
AZURE_LOCATION=${LOCATION}
AZURE_EXECUTION_IMAGE=${AZURE_EXECUTION_IMAGE}
AZURE_EXECUTION_REGISTRY_SERVER=${AZURE_EXECUTION_REGISTRY_SERVER}
AZURE_EXECUTION_REGISTRY_USERNAME=${AZURE_EXECUTION_REGISTRY_USERNAME}
AZURE_EXECUTION_REGISTRY_PASSWORD=${AZURE_EXECUTION_REGISTRY_PASSWORD}
AZURE_EXECUTION_TIMEOUT_SECONDS=30
AZURE_EXECUTION_CPU=0.5
AZURE_EXECUTION_MEMORY_GB=1.0
AZURE_EXECUTION_POLL_INTERVAL_SECONDS=2
CORS_ORIGINS=http://localhost:3000
AZURE_BLOB_CONNECTION=${AZURE_BLOB_CONNECTION}
EOF
  echo -e "${GREEN}? Wrote generated environment file: ${GENERATED_ENV_PATH}${NC}"
  echo "Template reference: ${ENV_TEMPLATE_PATH}"
}

print_summary() {
  echo -e "\n${GREEN}========================================${NC}"
  echo -e "${GREEN}Deployment Complete${NC}"
  echo -e "${GREEN}========================================${NC}"

  echo -e "\n${YELLOW}Resources${NC}"
  echo "Resource Group: ${RESOURCE_GROUP}"
  echo "ACR: ${REGISTRY_URL}"
  echo "Image: ${FULL_IMAGE_NAME}"
  echo "PostgreSQL Host: ${POSTGRES_HOST}"
  echo "Redis Host: ${REDIS_HOST}"
  echo "App Service URL: ${APP_SERVICE_URL}"
  if [[ "$DEPLOY_CONTAINER_APPS" == "y" ]]; then
    echo "Container App URL: ${CONTAINER_APP_URL}"
  fi

  echo -e "\n${YELLOW}Useful Commands${NC}"
  echo "App Service logs: az webapp log tail --resource-group ${RESOURCE_GROUP} --name ${APP_NAME}"
  if [[ "$DEPLOY_CONTAINER_APPS" == "y" ]]; then
    echo "Container App logs: az containerapp logs show --name ${CONTAINERAPP_NAME} --resource-group ${RESOURCE_GROUP} --follow"
  fi
  echo "Delete resource group: az group delete --name ${RESOURCE_GROUP} --yes --no-wait"
}

main() {
  print_header
  ensure_env_template
  get_config

  read -r -p "Continue with deployment? (y/N): " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
  fi

  check_prerequisites
  login_azure
  create_resource_group
  create_container_registry
  build_and_push_image
  create_postgres
  create_redis
  create_blob_storage_optional
  configure_runtime_env_values
  create_app_service_plan
  deploy_app_service
  deploy_container_apps_optional
  write_generated_env_file

  health_check_url "$APP_SERVICE_URL"
  if [[ "$DEPLOY_CONTAINER_APPS" == "y" ]]; then
    health_check_url "$CONTAINER_APP_URL"
  fi

  print_summary
}

main "$@"
