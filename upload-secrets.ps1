# upload-secrets.ps1
# Script para subir secretos a GitHub usando la CLI gh estructurada para Swarm

Write-Host "Iniciando subida de secretos estructurados a GitHub para HomologaSys..."

# Solicitar interactivamente los datos sensibles para no exponerlos en el código de Git
$GHCR_PATH = Read-Host -Prompt "Ingresa tu GitHub Personal Access Token (GHCR_PATH)"
$VPS_SSH_KEY = Read-Host -Prompt "Ingresa la contraseña/llave de tu VPS (VPS_SSH_KEY)"

if (-not $GHCR_PATH -or -not $VPS_SSH_KEY) {
    Write-Error "El token GHCR_PATH y la clave VPS_SSH_KEY son obligatorios para continuar."
    exit 1
}

# 1. Subir variables del VPS de forma estructurada
Write-Host "Subiendo VPS_HOST..."
gh secret set VPS_HOST --body "161.97.140.245"

Write-Host "Subiendo VPS_USER..."
gh secret set VPS_USER --body "1803980844"

Write-Host "Subiendo VPS_SSH_KEY..."
gh secret set VPS_SSH_KEY --body $VPS_SSH_KEY

Write-Host "Subiendo VPS_SSH_PORT..."
gh secret set VPS_SSH_PORT --body "1987"

# 2. Subir Token de GitHub con el nuevo nombre GHCR_PATH
Write-Host "Subiendo GHCR_PATH..."
gh secret set GHCR_PATH --body $GHCR_PATH

# 3. Subir variables de entorno de producción
Write-Host "Subiendo variables de entorno de producción..."
gh secret set FLASK_CONFIG --body "production"
gh secret set SECRET_KEY --body "clave_secreta_homologaciones_2026"
gh secret set POSTGRES_USER --body "bmoreno"
gh secret set POSTGRES_PASSWORD --body "seMoreno%"
gh secret set POSTGRES_DB --body "homologasys"
gh secret set POSTGRES_HOST --body "dbhomologaciones"
gh secret set POSTGRES_PORT --body "5432"

# 4. Leer archivo .env y subir cualquier otra variable de forma dinámica (por ejemplo, credenciales de correo)
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -and -not $_.StartsWith("#")) {
            if ($_ -match "^(.*?)=(.*)$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                
                # Quitar comillas si el valor las tiene envueltas
                if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                if ($value.StartsWith("'") -and $value.EndsWith("'")) {
                    $value = $value.Substring(1, $value.Length - 2)
                }

                # Evitar resubir las que ya subimos explícitamente
                $exclude_keys = @(
                    "FLASK_CONFIG", "SECRET_KEY", "POSTGRES_USER", "POSTGRES_PASSWORD", 
                    "POSTGRES_DB", "POSTGRES_HOST", "POSTGRES_PORT", 
                    "VPS_HOST", "VPS_USER", "VPS_SSH_KEY", "VPS_SSH_PORT", "GHCR_PATH"
                )
                if ($exclude_keys -notcontains $key) {
                    Write-Host "Subiendo $key..."
                    gh secret set $key --body $value
                }
            }
        }
    }
}

Write-Host "¡Proceso de carga de secretos Swarm para HomologaSys finalizado con éxito!"
