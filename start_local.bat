@echo off
echo ========================================
echo   LAPOAITOOLS BACKEND - LOCAL DEV
echo ========================================
echo.

echo Checking environment...
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env and add your Cloudinary credentials!
    echo.
    pause
)

echo Running migrations...
python manage.py migrate
echo.

echo Creating superuser (if needed)...
python ensuresuperuser.py
echo.

echo ========================================
echo   Starting Django server...
echo ========================================
echo.
echo API will be available at: http://localhost:8000
echo Admin login: aseeb / Dr.aseeb123
echo.
python manage.py runserver
