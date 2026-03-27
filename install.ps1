#Requires -Version 5.1

<#
Run with:
  powershell -ExecutionPolicy Bypass -File .\install.ps1
#>

param()

$ErrorActionPreference = 'Stop'

$Script:WindowsVersion = $null
$Script:WindowsEdition = $null
$Script:PackageManager = $null
$Script:RepoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { 'https://github.com/example/dicom_transfer_pipeline.git' }
$Script:InstallDir = if ($env:INSTALL_DIR) { $env:INSTALL_DIR } else { Join-Path $HOME 'dicom_transfer_pipeline' }
$Script:ProjectRoot = $null
$Script:StartTarget = if ($env:START_TARGET) { $env:START_TARGET } else { 'guardian' }

function Write-InfoMessage {
  Write-Host "→ $args" -ForegroundColor Cyan
}

function Write-SuccessMessage {
  Write-Host "✓ $args" -ForegroundColor Green
}

function Write-ErrorMessage {
  Write-Host "✗ $args" -ForegroundColor Red
}

function Test-ExecutionPolicyReadiness {
  $policy = Get-ExecutionPolicy -Scope CurrentUser
  if ($policy -eq 'Restricted') {
    throw 'Execution policy is Restricted. Re-run with -ExecutionPolicy Bypass or update the CurrentUser policy.'
  }
}

function Get-WindowsDetails {
  $os = Get-CimInstance -ClassName Win32_OperatingSystem
  $Script:WindowsVersion = $os.Version
  $Script:WindowsEdition = $os.Caption
}

function Get-PackageManager {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    $Script:PackageManager = 'winget'
    return
  }

  if (Get-Command choco -ErrorAction SilentlyContinue) {
    $Script:PackageManager = 'choco'
    return
  }

  $Script:PackageManager = 'unknown'
}

function Install-SystemDependencies {
  $missing = @()

  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { $missing += 'Git.Git' }
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += 'Python.Python.3.11' }
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { $missing += 'OpenJS.NodeJS' }
  if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) { $missing += 'ShiningLight.OpenSSL.Light' }

  if ($missing.Count -eq 0) {
    Write-SuccessMessage 'System dependencies already available'
    return
  }

  Write-InfoMessage "Installing Windows dependencies with $($Script:PackageManager)"
  switch ($Script:PackageManager) {
    'winget' {
      foreach ($package in $missing) {
        winget install --id $package --accept-source-agreements --accept-package-agreements
      }
    }
    'choco' {
      foreach ($package in $missing) {
        switch ($package) {
          'Git.Git' { choco install git -y }
          'Python.Python.3.11' { choco install python --version=3.11.9 -y }
          'OpenJS.NodeJS' { choco install nodejs-lts -y }
          'ShiningLight.OpenSSL.Light' { choco install openssl.light -y }
        }
      }
    }
    default {
      throw 'No supported Windows package manager was found.'
    }
  }
  Write-SuccessMessage 'System dependency installation completed'
}

function Initialize-Repository {
  if (Test-Path (Join-Path $Script:InstallDir '.git')) {
    $Script:ProjectRoot = $Script:InstallDir
    Write-InfoMessage "Updating existing repository in $($Script:ProjectRoot)"
    git -C $Script:ProjectRoot pull --ff-only
    Write-SuccessMessage 'Repository updated'
    return
  }

  if ((Test-Path $Script:InstallDir) -and (Get-ChildItem -Force $Script:InstallDir -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    $Script:ProjectRoot = $Script:InstallDir
    Write-InfoMessage "Using existing directory at $($Script:ProjectRoot)"
    return
  }

  Write-InfoMessage "Cloning repository into $($Script:InstallDir)"
  git clone $Script:RepoUrl $Script:InstallDir
  $Script:ProjectRoot = $Script:InstallDir
  Write-SuccessMessage 'Repository cloned'
}

function Install-ProjectDependencies {
  $guardianDir = Join-Path $Script:ProjectRoot 'dicom_guardian'
  if (Test-Path $guardianDir) {
    Write-InfoMessage 'Installing Python dependencies'
    Push-Location $guardianDir
    try {
      if (-not (Test-Path '.venv')) {
        python -m venv .venv
      }
      & .\.venv\Scripts\python.exe -m pip install --upgrade pip
      & .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    }
    finally {
      Pop-Location
    }
    Write-SuccessMessage 'Python environment ready'
  }

  $uiDir = Join-Path $Script:ProjectRoot 'dicom_ui'
  if (Test-Path $uiDir) {
    Write-InfoMessage 'Installing Node.js workspace dependencies'
    Push-Location $uiDir
    try {
      npm ci
    }
    finally {
      Pop-Location
    }
    Write-SuccessMessage 'Node.js dependencies ready'
  }
}

function Initialize-Environment {
  $rootExample = Join-Path $Script:ProjectRoot '.env.example'
  $rootEnv = Join-Path $Script:ProjectRoot '.env'
  if ((Test-Path $rootExample) -and (-not (Test-Path $rootEnv))) {
    Copy-Item $rootExample $rootEnv
    Write-SuccessMessage 'Created .env from example'
  }

  $guardianExample = Join-Path $Script:ProjectRoot 'dicom_guardian\.env.example'
  $guardianEnv = Join-Path $Script:ProjectRoot 'dicom_guardian\.env'
  if ((Test-Path $guardianExample) -and (-not (Test-Path $guardianEnv))) {
    Copy-Item $guardianExample $guardianEnv
    Write-SuccessMessage 'Created dicom_guardian\.env from example'
  }

  $uiExample = Join-Path $Script:ProjectRoot 'dicom_ui\.env.example'
  $uiEnv = Join-Path $Script:ProjectRoot 'dicom_ui\.env'
  if ((Test-Path $uiExample) -and (-not (Test-Path $uiEnv))) {
    Copy-Item $uiExample $uiEnv
    Write-SuccessMessage 'Created dicom_ui\.env from example'
  }

  $frontendExample = Join-Path $Script:ProjectRoot 'dicom_ui\frontend\.env.example'
  $frontendEnv = Join-Path $Script:ProjectRoot 'dicom_ui\frontend\.env'
  if ((Test-Path $frontendExample) -and (-not (Test-Path $frontendEnv))) {
    Copy-Item $frontendExample $frontendEnv
    Write-SuccessMessage 'Created dicom_ui\frontend\.env from example'
  }
}

function Invoke-BuildProcess {
  $tlsScript = Join-Path $Script:ProjectRoot 'scripts\generate_tls_certs.sh'
  if (Test-Path $tlsScript) {
    Write-InfoMessage 'Generating local TLS certificates'
    bash $tlsScript
    Write-SuccessMessage 'TLS certificates generated'
  }

  $uiDir = Join-Path $Script:ProjectRoot 'dicom_ui'
  if (Test-Path $uiDir) {
    Write-InfoMessage 'Building frontend workspace'
    Push-Location $uiDir
    try {
      npm run build --workspace frontend
    }
    finally {
      Pop-Location
    }
    Write-SuccessMessage 'Frontend build completed'
  }
}

function Start-Application {
  Write-InfoMessage "Starting application target: $($Script:StartTarget)"
  switch ($Script:StartTarget) {
    'guardian' {
      Push-Location (Join-Path $Script:ProjectRoot 'dicom_guardian')
      try {
        & .\.venv\Scripts\python.exe -m app.main
      }
      finally {
        Pop-Location
      }
    }
    'ui-backend' {
      Push-Location (Join-Path $Script:ProjectRoot 'dicom_ui\backend')
      try {
        npm start
      }
      finally {
        Pop-Location
      }
    }
    'ui-frontend' {
      Push-Location (Join-Path $Script:ProjectRoot 'dicom_ui\frontend')
      try {
        npm run dev -- --host 0.0.0.0
      }
      finally {
        Pop-Location
      }
    }
    default {
      throw "Unsupported START_TARGET: $($Script:StartTarget)"
    }
  }
}

function Main {
  try {
    Test-ExecutionPolicyReadiness
    Get-WindowsDetails
    Get-PackageManager
    Install-SystemDependencies
    Initialize-Repository
    Install-ProjectDependencies
    Initialize-Environment
    Invoke-BuildProcess
    Start-Application
  }
  catch {
    Write-ErrorMessage $_.Exception.Message
    throw
  }
}

Main
