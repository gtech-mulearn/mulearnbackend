<#
Running tests (Windows PowerShell)
----------------------------------
  scripts\test.ps1 [pytest arguments or paths]
      The SQLite tier: an in-memory database, never a real one, whatever .env says.
      Runs every test not marked @pytest.mark.mysql.
  scripts\test.ps1 -Mysql [pytest arguments or paths]
      The MySQL tier: tests marked @pytest.mark.mysql, against a local test database.
      Set TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME, TEST_DB_USER and TEST_DB_PASSWORD to change
      the defaults (127.0.0.1, 3306, test_mulearn, root, local-only).

Same behaviour as scripts/test.sh: -Mysql counts only as the first argument, and everything else
goes to pytest unchanged. Paths are relative to the repository root. $env:PYTHON picks the
interpreter (default: python). See docs/architecture/12-testing-and-quality-gates.md.
#>
# No param() block on purpose: declared parameters would capture pytest flags by abbreviation
# (-p would bind to a -PytestArgs parameter, -m to -Mysql).
$PytestArgs = @($args)
$Mysql = $false
if ($PytestArgs.Count -gt 0 -and $PytestArgs[0] -eq "-Mysql") {
    $Mysql = $true
    $PytestArgs = @($PytestArgs | Select-Object -Skip 1)
}

Set-Location (Join-Path $PSScriptRoot "..")
$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

if (-not (Test-Path ".env")) {
    [Console]::Error.WriteLine("No .env found: copy .env.sample to .env first.")
    exit 1
}
& $python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)"
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("pytest isn't installed for ${python}: run pip install pytest.")
    exit 1
}

# The logging settings fail at startup if the log directory is missing.
$logDir = $env:LOGGER_DIR_PATH
if (-not $logDir) {
    $line = Get-Content ".env" | Where-Object { $_ -match '^\s*LOGGER_DIR_PATH\s*=' } | Select-Object -Last 1
    if ($line) { $logDir = ($line -replace '^\s*LOGGER_DIR_PATH\s*=\s*', '').Trim().Trim('"', "'") }
}
if (-not $logDir) { $logDir = "./logs" }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Environment variables win over .env, because decouple reads the environment first.
if ($Mysql) {
    $env:DATABASE_ENGINE = "django.db.backends.mysql"
    $env:DATABASE_HOST = if ($env:TEST_DB_HOST) { $env:TEST_DB_HOST } else { "127.0.0.1" }
    $env:DATABASE_PORT = if ($env:TEST_DB_PORT) { $env:TEST_DB_PORT } else { "3306" }
    $env:DATABASE_NAME = if ($env:TEST_DB_NAME) { $env:TEST_DB_NAME } else { "test_mulearn" }
    $env:DATABASE_USER = if ($env:TEST_DB_USER) { $env:TEST_DB_USER } else { "root" }
    $env:DATABASE_PASSWORD = if ($env:TEST_DB_PASSWORD) { $env:TEST_DB_PASSWORD } else { "local-only" }
    & $python scripts/check_test_mysql.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m pytest @PytestArgs --import-mode=importlib -m mysql
    exit $LASTEXITCODE
}

$env:DATABASE_ENGINE = "django.db.backends.sqlite3"
$env:DATABASE_NAME = ":memory:"
# PowerShell can't hold an empty environment variable (assigning "" removes it). These four are
# removed instead; SQLite ignores them, and the engine and name above decide the database.
foreach ($name in "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_HOST", "DATABASE_PORT") {
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}
& $python -m pytest @PytestArgs --import-mode=importlib -m "not mysql"
exit $LASTEXITCODE
