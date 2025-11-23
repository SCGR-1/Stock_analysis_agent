@echo off
REM Windows batch file for local development
REM Usage: dev.bat [command]

if "%1"=="build" goto build
if "%1"=="start" goto start
if "%1"=="ingest" goto ingest
if "%1"=="agent" goto agent
if "%1"=="maint" goto maint
if "%1"=="web" goto web
if "%1"=="test" goto test
goto help

:build
echo Building SAM application...
cd infra
sam build
cd ..
goto end

:start
echo Starting local API Gateway on port 3000...
cd infra
sam local start-api --port 3000 --env-vars ../sam-env.json
cd ..
goto end

:ingest
echo Testing ingestion function locally...
cd infra
sam local invoke StoxIngestFunction --event ..\test-payload.json --env-vars ../sam-env.json
cd ..
goto end

:agent
echo Testing agent function locally...
cd infra
sam local invoke StoxAgentFunction --event ..\agent-payload.json --env-vars ../sam-env.json
cd ..
goto end

:maint
echo Testing maintenance function locally...
cd infra
sam local invoke StoxMaintFunction --event "{}" --env-vars ../sam-env.json
cd ..
goto end

:web
echo Serving web interface on port 8000...
cd web
python -m http.server 8000
cd ..
goto end

:test
echo Running unit tests...
python -m pytest tests/ -v
goto end

:help
echo Available commands:
echo   build   - Build SAM application
echo   start   - Start local API Gateway (port 3000)
echo   ingest  - Test ingestion function locally
echo   agent   - Test agent function locally
echo   maint   - Test maintenance function locally
echo   web     - Serve web interface (port 8000)
echo   test    - Run unit tests
echo   help    - Show this help
echo.
echo Example: dev.bat start
goto end

:end
