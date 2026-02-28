#!/bin/bash

# Azure Deployment Script for Cloud-Native Code Judge
# Description: Deploy the code judge to Azure using ACR and App Service

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Cloud-Native Code Judge - Azure Deploy${NC}"
echo -e "${GREEN}========================================${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    if ! command -v az &> /dev/null; then
        echo -e "${RED}Error: Azure CLI not found. Please install it first.${NC}"
        echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker not found. Please install it first.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Prerequisites met${NC}"
}

# Get configuration from user
get_config() {
    echo -e "\n${YELLOW}Configuration:${NC}"
    
    read -p "Enter Azure subscription ID: " SUBSCRIPTION_ID
    read -p "Enter resource group name: " RESOURCE_GROUP
    read -p "Enter location (e.g., eastus, westus): " LOCATION
    read -p "Enter container registry name (lowercase, no hyphens): " REGISTRY_NAME
    read -p "Enter app name for App Service: " APP_NAME
    read -p "Enter storage account name for persistent file sharing (optional, press enter to skip): " STORAGE_ACCOUNT
    
    echo -e "\n${YELLOW}Configuration Summary:${NC}"
    echo "Subscription: $SUBSCRIPTION_ID"
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Location: $LOCATION"
    echo "Container Registry: ${REGISTRY_NAME}.azurecr.io"
    echo "App Service Name: $APP_NAME"
}

# Login to Azure
login_azure() {
    echo -e "\n${YELLOW}Logging in to Azure...${NC}"
    az login
    az account set --subscription "$SUBSCRIPTION_ID"
    echo -e "${GREEN}✓ Logged into Azure${NC}"
}

# Create resource group
create_resource_group() {
    echo -e "\n${YELLOW}Creating resource group: $RESOURCE_GROUP${NC}"
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION"
    echo -e "${GREEN}✓ Resource group created${NC}"
}

# Create Azure Container Registry
create_container_registry() {
    echo -e "\n${YELLOW}Creating Azure Container Registry: $REGISTRY_NAME${NC}"
    az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --sku Basic \
        --admin-enabled true
    echo -e "${GREEN}✓ Container Registry created${NC}"
}

# Build and push Docker image
build_and_push_image() {
    echo -e "\n${YELLOW}Building and pushing Docker image...${NC}"
    
    REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"
    IMAGE_NAME="code-judge"
    IMAGE_TAG="latest"
    FULL_IMAGE_NAME="$REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG"
    
    # Get ACR credentials
    REGISTRY_USERNAME=$(az acr credential show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --query "username" -o tsv)
    
    REGISTRY_PASSWORD=$(az acr credential show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --query "passwords[0].value" -o tsv)
    
    # Login to ACR using Docker
    echo "$REGISTRY_PASSWORD" | docker login -u "$REGISTRY_USERNAME" --password-stdin "$REGISTRY_URL"
    
    # Build image
    docker build -t "$FULL_IMAGE_NAME" .
    
    # Push image
    docker push "$FULL_IMAGE_NAME"
    
    echo -e "${GREEN}✓ Docker image pushed to ACR${NC}"
    echo "Image: $FULL_IMAGE_NAME"
}

# Create App Service plan
create_app_service_plan() {
    echo -e "\n${YELLOW}Creating App Service plan...${NC}"
    
    PLAN_NAME="${RESOURCE_GROUP}-plan"
    
    az appservice plan create \
        --name "$PLAN_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --sku B1 \
        --is-linux
    
    echo -e "${GREEN}✓ App Service plan created${NC}"
}

# Create App Service
create_app_service() {
    echo -e "\n${YELLOW}Creating App Service (Web App)...${NC}"
    
    PLAN_NAME="${RESOURCE_GROUP}-plan"
    REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"
    IMAGE_NAME="code-judge"
    IMAGE_TAG="latest"
    FULL_IMAGE_NAME="$REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG"
    
    # Create web app
    az webapp create \
        --resource-group "$RESOURCE_GROUP" \
        --plan "$PLAN_NAME" \
        --name "$APP_NAME" \
        --deployment-container-image-name "$FULL_IMAGE_NAME"
    
    # Configure container registry
    REGISTRY_USERNAME=$(az acr credential show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --query "username" -o tsv)
    
    REGISTRY_PASSWORD=$(az acr credential show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --query "passwords[0].value" -o tsv)
    
    az webapp config container set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$APP_NAME" \
        --docker-custom-image-name "$FULL_IMAGE_NAME" \
        --docker-registry-server-url "https://$REGISTRY_URL" \
        --docker-registry-server-user "$REGISTRY_USERNAME" \
        --docker-registry-server-password "$REGISTRY_PASSWORD"
    
    # Set environment variables
    az webapp config appsettings set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$APP_NAME" \
        --settings \
            WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
            WEBSITES_PORT=8000 \
            SECRET_KEY="$(openssl rand -hex 32)" \
            DATABASE_URL="sqlite:///./judge.db"
    
    echo -e "${GREEN}✓ App Service created${NC}"
}

# Deploy to Container Instances (optional)
deploy_to_container_instances() {
    read -p "Deploy to Azure Container Instances as well? (y/n): " deploy_aci
    
    if [ "$deploy_aci" != "y" ]; then
        return
    fi
    
    echo -e "\n${YELLOW}Deploying to Azure Container Instances...${NC}"
    
    REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"
    IMAGE_NAME="code-judge"
    IMAGE_TAG="latest"
    FULL_IMAGE_NAME="$REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG"
    
    REGISTRY_USERNAME=$(az acr credential show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --query "username" -o tsv)
    
    REGISTRY_PASSWORD=$(az acr credential show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REGISTRY_NAME" \
        --query "passwords[0].value" -o tsv)
    
    az container create \
        --resource-group "$RESOURCE_GROUP" \
        --name "${APP_NAME}-aci" \
        --image "$FULL_IMAGE_NAME" \
        --cpu 1 \
        --memory 1 \
        --port 8000 \
        --dns-name-label "${APP_NAME}-aci" \
        --registry-login-server "$REGISTRY_URL" \
        --registry-username "$REGISTRY_USERNAME" \
        --registry-password "$REGISTRY_PASSWORD" \
        --environment-variables SECRET_KEY="$(openssl rand -hex 32)" DATABASE_URL="sqlite:///./judge.db"
    
    echo -e "${GREEN}✓ Deployed to Azure Container Instances${NC}"
    
    FQDN=$(az container show \
        --resource-group "$RESOURCE_GROUP" \
        --name "${APP_NAME}-aci" \
        --query ipAddress.fqdn -o tsv)
    
    echo -e "${GREEN}Container Instances URL: http://$FQDN:8000${NC}"
}

# Print deployment summary
print_summary() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    echo -e "\n${YELLOW}Resource Details:${NC}"
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Container Registry: ${REGISTRY_NAME}.azurecr.io"
    echo "App Service URL: https://${APP_NAME}.azurewebsites.net"
    
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Monitor deployment: az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME"
    echo "2. Check health: curl https://${APP_NAME}.azurewebsites.net/health"
    echo "3. API Documentation: https://${APP_NAME}.azurewebsites.net/docs"
    
    echo -e "\n${YELLOW}Useful Commands:${NC}"
    echo "View logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME --provider docker"
    echo "Scale up: az appservice plan update --name $PLAN_NAME --resource-group $RESOURCE_GROUP --sku S1"
    echo "Delete resources: az group delete --name $RESOURCE_GROUP"
}

# Main execution
main() {
    check_prerequisites
    get_config
    
    read -p "Continue with deployment? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    login_azure
    create_resource_group
    create_container_registry
    build_and_push_image
    create_app_service_plan
    create_app_service
    deploy_to_container_instances
    print_summary
}

main "$@"
