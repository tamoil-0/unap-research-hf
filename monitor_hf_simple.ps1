#!/usr/bin/env pwsh
# Monitor simple de HF Spaces rebuild

$url = "https://tamoil13-unap-research-ml.hf.space/health"

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host " MONITOR DE HF SPACES REBUILD" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Monitoreando cada 15 segundos..." -ForegroundColor Yellow
Write-Host ""

for($i = 1; $i -le 30; $i++) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        $content = $response.Content | ConvertFrom-Json
        
        if ($content.PSObject.Properties.Name -contains "index_loaded") {
            Write-Host "[$timestamp] EXITO - Codigo nuevo detectado!" -ForegroundColor Green
            Write-Host ""
            $content | ConvertTo-Json
            Write-Host ""
            
            if ($content.index_loaded -eq $true) {
                Write-Host "Indice FAISS cargado: SI ($($content.index_count) vectores)" -ForegroundColor Green
            } else {
                Write-Host "Indice FAISS cargado: NO" -ForegroundColor Red
            }
            
            exit 0
        } else {
            Write-Host "[$timestamp] Codigo antiguo (intento $i/30)" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "[$timestamp] Offline - rebuilding (intento $i/30)" -ForegroundColor Gray
    }
    
    if ($i -lt 30) {
        Start-Sleep -Seconds 15
    }
}

Write-Host ""
Write-Host "Timeout - revisa logs en HF Spaces" -ForegroundColor Red
exit 1
