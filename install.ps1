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
