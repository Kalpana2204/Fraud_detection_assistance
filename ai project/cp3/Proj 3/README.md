# Fraud Detection Assistant

A modern web application that helps users detect and get notified about suspicious transactions using Google's Gemini AI.

## Features
- Real-time transaction monitoring
- AI-powered fraud detection
- User-friendly dashboard
- Transaction history
- Customizable notification settings
- Dark theme interface

## Setup Instructions

1. Install Python 3.8 or higher
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
4. Run migrations:
   ```
   python manage.py migrate
   ```
5. Start the development server:
   ```
   python manage.py runserver
   ```
6. Access the application at `http://127.0.0.1:8000`

## Security Note
- Keep your API keys secure
- Never commit the `.env` file to version control
- Use HTTPS in production 