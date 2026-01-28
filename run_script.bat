@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Running script...
python generate_reports.py
echo.
echo Done! Check the generated PDF files.
pause
