@echo off
echo Starting Serverless AI Stock Analytics locally...
echo.

echo Building SAM application...
cd infra
sam build
cd ..

echo Starting API Gateway on port 3000...
start "API Gateway" cmd /k "cd infra && sam local start-api --port 3000"

echo Starting Web Interface on port 8000...
start "Web Interface" cmd /k "cd web && python -m http.server 8000"

echo.
echo Services starting...
echo - API Gateway: http://localhost:3000
echo - Web Interface: http://localhost:8000
echo.
echo Press any key to open the web interface...
pause >nul

start http://localhost:8000
