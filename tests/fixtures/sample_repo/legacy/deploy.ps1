# Script PowerShell: linguaggio del set MVP senza grammatica matura -> chunking dimensionale (fallback).
function Deploy-App {
    param([string]$Name)
    Write-Host "Deploying $Name"
}

Deploy-App -Name "demo"
