# Running Instructions - Cloud-Native Code Judge

## Local Development (GitHub Codespaces or Linux/Mac)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

The API will be available at:
- **Web UI:** http://localhost:8000
- **Swagger UI (Interactive Docs):** http://localhost:8000/docs
- **ReDoc (API Docs):** http://localhost:8000/redoc

### 3. Test the API
```bash
# Run the test script to verify all endpoints
chmod +x test_api.sh
./test_api.sh
```

Or manually test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Register a user
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Login to get JWT token
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

## Docker Deployment (Local)

### Build Docker Image
```bash
docker build -t code-judge:latest .
```

### Run Docker Container
```bash
docker run -d \
  --name code-judge \
  -p 8000:8000 \
  -e SECRET_KEY="change-this-in-production" \
  -e DATABASE_URL="sqlite:///./judge.db" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  code-judge:latest
```

**Note:** For code execution sandbox to work, mount Docker socket: `-v /var/run/docker.sock:/var/run/docker.sock`

### Stop Container
```bash
docker stop code-judge
docker rm code-judge
```

## Azure Deployment

### Prerequisites
- Azure CLI installed: https://docs.microsoft.com/cli/azure/install-azure-cli
- Docker installed locally
- Active Azure subscription

### Automated Deployment (Recommended)
```bash
chmod +x azure_deploy.sh
./azure_deploy.sh
```

This interactive script will:
1. Prompt for Azure configuration (subscription, resource group, location, etc.)
2. Create Azure Container Registry
3. Build and push Docker image to ACR
4. Create App Service plan
5. Deploy web app to Azure App Service
6. Optionally deploy to Azure Container Instances

### Manual Azure Deployment

#### Step 1: Create Resource Group
```bash
az group create \
  --name my-judge-rg \
  --location eastus
```

#### Step 2: Create Container Registry
```bash
az acr create \
  --resource-group my-judge-rg \
  --name myjudgeregistry \
  --sku Basic
```

#### Step 3: Build and Push Image
```bash
az acr build \
  --registry myjudgeregistry \
  --image code-judge:latest .
```

#### Step 4: Create App Service Plan
```bash
az appservice plan create \
  --name judge-plan \
  --resource-group my-judge-rg \
  --sku B1 \
  --is-linux
```

#### Step 5: Create Web App
```bash
az webapp create \
  --resource-group my-judge-rg \
  --plan judge-plan \
  --name my-code-judge \
  --deployment-container-image-name myjudgeregistry.azurecr.io/code-judge:latest
```

#### Step 6: Configure Container Registry
```bash
REGISTRY_USERNAME=$(az acr credential show \
  --resource-group my-judge-rg \
  --name myjudgeregistry \
  --query "username" -o tsv)

REGISTRY_PASSWORD=$(az acr credential show \
  --resource-group my-judge-rg \
  --name myjudgeregistry \
  --query "passwords[0].value" -o tsv)

az webapp config container set \
  --resource-group my-judge-rg \
  --name my-code-judge \
  --docker-custom-image-name myjudgeregistry.azurecr.io/code-judge:latest \
  --docker-registry-server-url https://myjudgeregistry.azurecr.io \
  --docker-registry-server-user "$REGISTRY_USERNAME" \
  --docker-registry-server-password "$REGISTRY_PASSWORD"
```

#### Step 7: Configure Application Settings
```bash
az webapp config appsettings set \
  --resource-group my-judge-rg \
  --name my-code-judge \
  --settings \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
    WEBSITES_PORT=8000 \
    SECRET_KEY="$(openssl rand -hex 32)" \
    DATABASE_URL="sqlite:///./judge.db"
```

### Access Your Deployed Application
- **URL:** https://my-code-judge.azurewebsites.net
- **API Docs:** https://my-code-judge.azurewebsites.net/docs
- **Health Check:** https://my-code-judge.azurewebsites.net/health

### Monitor Deployment
```bash
# View application logs
az webapp log tail \
  --resource-group my-judge-rg \
  --name my-code-judge \
  --provider docker

# View deployment history
az webapp deployment list \
  --resource-group my-judge-rg \
  --name my-code-judge
```

## Azure Container Instances Deployment (Alternative)

For simple deployments without App Service:

```bash
REGISTRY_USERNAME=$(az acr credential show \
  --resource-group my-judge-rg \
  --name myjudgeregistry \
  --query "username" -o tsv)

REGISTRY_PASSWORD=$(az acr credential show \
  --resource-group my-judge-rg \
  --name myjudgeregistry \
  --query "passwords[0].value" -o tsv)

az container create \
  --resource-group my-judge-rg \
  --name code-judge-aci \
  --image myjudgeregistry.azurecr.io/code-judge:latest \
  --cpu 1 \
  --memory 1 \
  --port 8000 \
  --dns-name-label code-judge-demo \
  --registry-login-server myjudgeregistry.azurecr.io \
  --registry-username "$REGISTRY_USERNAME" \
  --registry-password "$REGISTRY_PASSWORD" \
  --environment-variables \
    SECRET_KEY="your-secret-key-here" \
    DATABASE_URL="sqlite:///./judge.db"
```

Access at: http://code-judge-demo.eastus.azurecontainer.io:8000

## Environment Variables

For development:
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./judge.db
```

For production (set in Azure):
```
SECRET_KEY=<randomly-generated-key>
DATABASE_URL=sqlite:///./judge.db
WEBSITES_ENABLE_APP_SERVICE_STORAGE=false
WEBSITES_PORT=8000
```

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
python -c "import uvicorn; uvicorn.run('app:app', host='0.0.0.0', port=8001)"
```

### Database Locked Error
```bash
# Remove SQLite database and restart
rm judge.db
python app.py
```

### Docker Not Available (Expected in Codespaces)
The application gracefully falls back to mock execution mode. Submissions will have a "warning" status.

### Azure Authentication Issues
```bash
# Login to Azure
az login

# Set correct subscription
az account set --subscription <subscription-id>

# Verify current settings
az account show
```

### Application Won't Start on Azure
```bash
# Check logs
az webapp log tail --resource-group <rg-name> --name <app-name>

# Restart app
az webapp restart --resource-group <rg-name> --name <app-name>
```

## Performance Tips

1. **Local Development:** Use SQLite for lightweight persistence
2. **Production:** Consider using Azure Database for PostgreSQL for better scalability
3. **Code Execution:** Set reasonable timeout limits (default: 10 seconds)
4. **Docker Resource Limits:** Memory (256MB) and CPU (0.5 cores) per execution

## Security Recommendations

1. **Generate unique SECRET_KEY for production**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Enable HTTPS in production** - Azure App Service automatically provides HTTPS

3. **Implement rate limiting** - Consider using `slowapi` library

4. **Keep dependencies updated**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

5. **Use Azure Key Vault for secrets** instead of environment variables

## Next Steps

1. Access the API documentation at `/docs` or `/redoc`
2. Register a user and create problems
3. Test the code execution sandbox
4. Monitor performance and adjust resource limits as needed
5. Explore Azure's monitoring and scaling options

## Support

For issues and questions:
- Check the main README.md for detailed information
- Review Azure documentation: https://docs.microsoft.com/azure/
- Check FastAPI docs: https://fastapi.tiangolo.com/

---

**Application is ready for deployment!** 🚀
