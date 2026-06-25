param(
  [string]$ProjectName = "jobflow-fabian"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  throw "Necesitas Node.js/npm para ejecutar npx vercel."
}

Write-Host "1) Login en Vercel (flujo seguro del proveedor; no pegues claves en el chat)."
npx vercel login

Write-Host "2) Vinculando proyecto: $ProjectName"
npx vercel link --yes --project $ProjectName

if (-not $env:AUTH_USER) {
  $env:AUTH_USER = Read-Host "Usuario para login del dashboard"
}
if (-not $env:AUTH_PASSWORD) {
  $chars = (48..57 + 65..90 + 97..122)
  $env:AUTH_PASSWORD = -join ($chars | Get-Random -Count 28 | ForEach-Object {[char]$_})
  Write-Host "Clave generada para este despliegue. Guárdala en un lugar seguro: $($env:AUTH_PASSWORD)"
}

Write-Host "3) Configurando variables de entorno seguras en Vercel."
$env:AUTH_USER | npx vercel env add AUTH_USER production
$env:AUTH_PASSWORD | npx vercel env add AUTH_PASSWORD production

Write-Host "4) Desplegando producción."
npx vercel --prod --yes
