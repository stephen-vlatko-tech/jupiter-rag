@echo off
cd /d "%~dp0"
echo ============================================================
echo  Jupiter RAG — Starting up
echo ============================================================
echo.
echo [1/4] Installing / updating dependencies...
pip install -r requirements.txt -q
playwright install chromium --with-deps >nul 2>&1
echo.
echo [2/4] Fetching latest Jupiter fund factsheets...
python fetch_factsheets.py
echo.
echo [3/4] Starting local server on http://localhost:8000 ...
start "" cmd /k "python -m http.server 8000"
echo.
echo [4/4] Opening app in browser...
timeout /t 2 /nobreak >nul
start "" "http://localhost:8000/jupiter-rag.html"
echo.
echo Done. The app should now be open in your browser.
echo Close the server window when you are finished.
