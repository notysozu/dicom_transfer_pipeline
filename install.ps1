#Requires -Version 5.1

<#
Run with:
  powershell -ExecutionPolicy Bypass -File .\install.ps1
#>

param()

$Script:WindowsVersion = $null
$Script:WindowsEdition = $null
$Script:PackageManager = $null

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
