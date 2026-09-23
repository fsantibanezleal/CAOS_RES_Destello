# Create the two environments: .venv (tests, guards) and .venv-pipeline (the offline pipeline). Python 3.12.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -3.12 -m venv .venv
py -3.12 -m venv .venv-pipeline
.\.venv\Scripts\python.exe -m pip install -q --upgrade pip
.\.venv\Scripts\python.exe -m pip install -q -r requirements.txt -r requirements-dev.txt
.\.venv-pipeline\Scripts\python.exe -m pip install -q --upgrade pip
.\.venv-pipeline\Scripts\python.exe -m pip install -q -r requirements-precompute.txt -r requirements-dev.txt
Write-Host "setup: .venv and .venv-pipeline ready"
