# Deploy Legal Information Navigator Backend to Google Cloud Run (PowerShell)
param(
    [string]$ProjectId = $env:GOOGLE_CLOUD_PROJECT,
    [string]$Region = "us-central1",
    [string]$ServiceName = "legal-navigator-backend"
)

if (-not $ProjectId) {
    $ProjectId = "legal-ai-navigator"
}

$ImageName = "gcr.io/$ProjectId/${ServiceName}:latest"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Deploying Legal Information Navigator to Google Cloud Run" -ForegroundColor Cyan
Write-Host " Project:  $ProjectId"
Write-Host " Region:   $Region"
Write-Host " Service:  $ServiceName"
Write-Host " Image:    $ImageName"
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Build Container Image
Write-Host "--> Building container image with Google Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --project=$ProjectId --tag=$ImageName .

# 2. Deploy to Cloud Run
Write-Host "--> Deploying service to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --project=$ProjectId `
    --region=$Region `
    --image=$ImageName `
    --platform="managed" `
    --allow-unauthenticated `
    --set-env-vars="GEMINI_API_KEY=$($env:GEMINI_API_KEY),USE_VERTEX_AI=$($env:USE_VERTEX_AI)" `
    --memory="1Gi" `
    --cpu="1" `
    --min-instances="0" `
    --max-instances="10" `
    --timeout="60s"

# 3. Output Service URL
$ServiceUrl = gcloud run services describe $ServiceName --project=$ProjectId --region=$Region --format="value(status.url)"

Write-Host "=================================================================" -ForegroundColor Green
Write-Host " Successfully deployed to Google Cloud Run!" -ForegroundColor Green
Write-Host " Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host " Healthcheck: $ServiceUrl/health" -ForegroundColor Green
Write-Host " Evaluation:  $ServiceUrl/api/evaluation/run" -ForegroundColor Green
Write-Host " Docs:        $ServiceUrl/docs" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
