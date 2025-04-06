import os
import subprocess

def setup_project():
    # Create Django project
    subprocess.run(['django-admin', 'startproject', 'fraud_detection'])
    
    # Move into project directory
    os.chdir('fraud_detection')
    
    # Create main app
    subprocess.run(['python', 'manage.py', 'startapp', 'core'])
    
    # Create static and templates directories
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates/core', exist_ok=True)
    
    print("Project setup complete!")

if __name__ == "__main__":
    setup_project() 