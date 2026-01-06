# Monitor de rebuild de HF Spaces
# Espera hasta que el Space reinicie con código nuevo

$url = "https://tamoil13-unap-research-ml.hf.space/health"
$maxAttempts = 30
$interval = 15

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline -ForegroundColor Blue
Write-Host " ESPERANDO FACTORY REBUILD DE HF SPACES " -NoNewline -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Blue
Write-Host "`nMonitoreando cada $interval segundos (máximo $($maxAttempts * $interval / 60) minutos)...`n" -ForegroundColor Yellow

$startTime = Get-Date

for($i = 1; $i -le $maxAttempts; $i++) {
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds)
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $content = $response.Content | ConvertFrom-Json
        
        # Verificar si tiene los nuevos campos
        if ($null -ne $content.index_loaded) {
            Write-Host "[$timestamp] " -NoNewline
            Write-Host "🎉 ¡ÉXITO! CÓDIGO NUEVO DETECTADO" -ForegroundColor Green
            Write-Host "`nTiempo total: $elapsed segundos`n" -ForegroundColor Cyan
            
            Write-Host "Respuesta completa:" -ForegroundColor Blue
            $content | ConvertTo-Json
            
            Write-Host "`n✅ Estado del índice:" -ForegroundColor Yellow
            if ($content.index_loaded -eq $true) {
                Write-Host "   - Índice cargado: SÍ" -ForegroundColor Green
                Write-Host "   - Vectores: $($content.index_count)" -ForegroundColor Green
                Write-Host "   - Ready: $($content.ready)" -ForegroundColor Green
                
                if ($content.error) {
                    Write-Host "   - Error: $($content.error)" -ForegroundColor Red
                } else {
                    Write-Host "   - Sin errores" -ForegroundColor Green
                }
                
                Write-Host "`n🎯 ¡El API está completamente funcional!" -ForegroundColor Green
                Write-Host "Puedes probar la extensión Chrome ahora.`n" -ForegroundColor Cyan
            } else {
                Write-Host "   - Índice NO cargado" -ForegroundColor Red
                if ($content.error) {
                    Write-Host "   - Error: $($content.error)" -ForegroundColor Red
                }
            }
            
            exit 0
        } else {
            # Código antiguo aún
            Write-Host "[$timestamp] ⏳ Código antiguo (intento $i/$maxAttempts, ${elapsed}s)" -ForegroundColor Yellow
        }
        
    } catch {
        # Offline o error
        if ($_.Exception.Message -match "timed out") {
            Write-Host "[$timestamp] ⚪ Timeout - rebuilding (intento $i/$maxAttempts, ${elapsed}s)" -ForegroundColor Gray
        } elseif ($_.Exception.Response.StatusCode -eq 502 -or $_.Exception.Response.StatusCode -eq 503) {
            Write-Host "[$timestamp] 🔄 Space offline - rebuilding (intento $i/$maxAttempts, ${elapsed}s)" -ForegroundColor Cyan
        } else {
            Write-Host "[$timestamp] ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    if ($i -lt $maxAttempts) {
        Start-Sleep -Seconds $interval
    }
}

# Timeout
Write-Host "`n⚠️  TIMEOUT después de $($maxAttempts * $interval / 60) minutos" -ForegroundColor Red
Write-Host "`nPosibles causas:" -ForegroundColor Yellow
Write-Host "  1. El rebuild aún está en progreso (revisa logs)" -ForegroundColor White
Write-Host "  2. Hay un error en el build" -ForegroundColor White
Write-Host "  3. El Space no inició correctamente" -ForegroundColor White
Write-Host "`nRevisa los logs en:" -ForegroundColor Yellow
Write-Host "https://huggingface.co/spaces/tamoil13/unap-research-ml/logs" -ForegroundColor Cyan
Write-Host ""

exit 1
