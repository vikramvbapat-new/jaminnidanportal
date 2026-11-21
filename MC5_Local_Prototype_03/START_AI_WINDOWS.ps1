## जमीन निदान पोर्टल — AI-enabled Startup (Windows PowerShell)
## फक्त काल्पनिक चाचणी माहितीसाठी वापरा. API Key स्क्रीनवर दिसत नाही.
## वास्तविक प्रकरणे किंवा खरे नावे/जमीन तपशील या prototype मध्ये टाकू नका.

$ErrorActionPreference = "Stop"

Write-Host "`n=== जमीन निदान पोर्टल — AI सह सुरू करणे ===" -ForegroundColor Cyan
Write-Host "हे केवळ स्थानिक विकासक चाचणी साधन आहे. Production साठी नाही.`n" -ForegroundColor Yellow

# --- Safety gate ---
$confirm = Read-Host "फक्त काल्पनिक चाचणी माहिती वापरणार आहात याची पुष्टी द्या (yes)"
if ($confirm.Trim().ToLower() -notin @("hoy", "yes", "y")) {
    Write-Host "रद्द केले." -ForegroundColor Red
    exit 1
}

# --- Model selection ---
Write-Host "`nOpenAI Model ID (Enter = gpt-4o):" -ForegroundColor Green
Write-Host "  शिफारस: gpt-4o  |  किफायत: gpt-4o-mini" -ForegroundColor DarkGray
$model = Read-Host "Model"
if (-not $model.Trim()) { $model = "gpt-4o" }

# --- Secure API Key entry ---
Write-Host "`nOpenAI API Key (स्क्रीनवर दिसणार नाही):" -ForegroundColor Green
$apiKeySecure = Read-Host -AsSecureString "OPENAI_API_KEY"
$apiKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKeySecure)
)
if (-not $apiKey.Trim().StartsWith("sk-")) {
    Write-Host "API Key 'sk-' ने सुरू होत नाही. रद्द केले." -ForegroundColor Red
    exit 1
}

# --- Set env vars (in-process only, not saved) ---
$env:MC5_AI_PROVIDER       = "openai"
$env:MC5_AI_ALLOW_EXTERNAL = "true"
$env:MC5_AI_MODEL          = $model.Trim()
$env:OPENAI_API_KEY        = $apiKey.Trim()

Write-Host "`n  Provider: openai | Model: $($model.Trim()) | Key: sk-****" -ForegroundColor DarkGray
Write-Host "  (Session-only — key not saved to disk or git)" -ForegroundColor DarkGray

# --- Preflight (no network) ---
Write-Host "`nPreflight check..." -ForegroundColor Cyan
Set-Location f:\Vikram\JaminNidanPortal\MC5_Local_Prototype_03
& "f:\Vikram\JaminNidanPortal\.venv\Scripts\python.exe" -m scripts.check_live_ai_readiness
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight failed." -ForegroundColor Red; exit 1
}

# --- Start server ---
Write-Host "`n=== Server: http://127.0.0.1:8765 (AI enabled) ===" -ForegroundColor Cyan
& "f:\Vikram\JaminNidanPortal\.venv\Scripts\python.exe" -m uvicorn app.server:app --host 127.0.0.1 --port 8765 --reload
