#Requires -Version 5.1

<#
Run with:
  powershell -ExecutionPolicy Bypass -File .\install.ps1
#>

param()

$Script:WindowsVersion = $null
$Script:WindowsEdition = $null
$Script:PackageManager = $null
$Script:RepoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { 'https://github.com/example/dicom_transfer_pipeline.git' }
$Script:InstallDir = if ($env:INSTALL_DIR) { $env:INSTALL_DIR } else { Join-Path $HOME 'dicom_transfer_pipeline' }
$Script:ProjectRoot = $null

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
    return
  }

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
}

function Initialize-Repository {
  if (Test-Path (Join-Path $Script:InstallDir '.git')) {
    $Script:ProjectRoot = $Script:InstallDir
    git -C $Script:ProjectRoot pull --ff-only
    return
  }

  if ((Test-Path $Script:InstallDir) -and (Get-ChildItem -Force $Script:InstallDir -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    $Script:ProjectRoot = $Script:InstallDir
    return
  }

  git clone $Script:RepoUrl $Script:InstallDir
  $Script:ProjectRoot = $Script:InstallDir
}

function Install-ProjectDependencies {
  $guardianDir = Join-Path $Script:ProjectRoot 'dicom_guardian'
  if (Test-Path $guardianDir) {
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
  }

  $uiDir = Join-Path $Script:ProjectRoot 'dicom_ui'
  if (Test-Path $uiDir) {
    Push-Location $uiDir
    try {
      npm ci
    }
    finally {
      Pop-Location
    }
  }
}
