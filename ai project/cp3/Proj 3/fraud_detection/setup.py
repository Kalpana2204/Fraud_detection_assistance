import os
import subprocess
import sys

def setup_project():
    # Install dependencies
    print("Installing dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Run migrations
    print("\nRunning migrations...")
    subprocess.run(['python', 'manage.py', 'makemigrations'])
    subprocess.run(['python', 'manage.py', 'migrate'])
    
    # Initialize database
    print("\nInitializing database...")
    subprocess.run(['python', 'init_db.py'])
    
    print("\nSetup complete! You can now run the development server with:")
    print("python manage.py runserver")
    print("\nDefault superuser credentials:")
    print("Username: admin")
    print("Password: admin123")

if __name__ == "__main__":
    setup_project() 