@echo off
echo ========================================
echo   CLOUDINARY SETUP FOR LAPOAITOOLS
echo ========================================
echo.

echo Step 1: Installing dependencies...
pip install -r requirements.txt
echo.

echo Step 2: Creating .env file...
if not exist .env (
    copy .env.example .env
    echo ✓ Created .env file
    echo.
    echo IMPORTANT: Edit .env file and add your Cloudinary credentials!
    echo Get them from: https://cloudinary.com/console
    echo.
) else (
    echo .env file already exists
    echo.
)

echo Step 3: Running migrations...
python manage.py makemigrations
python manage.py migrate
echo.

echo ========================================
echo   SETUP COMPLETE!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your Cloudinary credentials
echo 2. Run: python manage.py runserver
echo.
echo See CLOUDINARY_SETUP.txt for detailed instructions
echo.
pause
