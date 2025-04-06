from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .models import Transaction, Notification, UserProfile
from django.http import JsonResponse
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from django.utils import timezone
from datetime import timedelta

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')

@login_required
def dashboard(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')[:10]
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'transactions': recent_transactions,
        'unread_notifications': unread_notifications,
        'user_profile': user_profile,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def analyze_transaction(request):
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            description = request.POST.get('description', '').strip()
            location = request.POST.get('location', '').strip()
            category = request.POST.get('category', '').strip()
            
            if not description:
                return JsonResponse({
                    'error': 'Description is required'
                }, status=400)
            
            # Create transaction
            transaction = Transaction.objects.create(
                user=request.user,
                amount=amount,
                description=description,
                location=location,
                category=category
            )
            
            # Analyze transaction using Gemini
            prompt = f"""
            You are a fraud detection expert. Analyze this transaction and provide a detailed risk assessment.
            give your prediction giving equal priorities to all categories .
            
            Transaction details:
            - Amount: ${amount}
            - Description: {description}
            - Location: {location}
            - Category: {category}
            
            Analyze the following aspects:
            1. Amount Risk:
               - Is the amount unusually high for this category?
               - Does it match typical spending patterns?
               - Is it significantly different from the user's average transaction?
            
            2. Location Risk:
               - Is the location suspicious or unusual?
               - Does it match the user's typical locations?
               - Is it a known high-risk location?
            
            3. Category Risk:
               - Does the category match the description?
               - Is this a typical category for the user?
               - Are there any red flags in the category?
            
            4. Pattern Analysis:
               - Is this transaction part of a suspicious pattern?
               - Does it deviate from normal spending behavior?
               - Are there any timing anomalies?
            
            Provide your analysis in JSON format with:
            {{
                "is_suspicious": boolean (true if any significant risk factors are present),
                "risk_score": float between 0 and 1 (0.7 or higher indicates high risk),
                "explanation": "Detailed explanation of your analysis, including specific risk factors identified and why they are concerning or not concerning. Provide clear reasoning for the risk score. Include specific details from the transaction that influenced your decision."
            }}
            
            Focus on providing specific, detailed analysis rather than generic statements.
            """
            
            try:
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Clean the response text to ensure it's valid JSON
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                # Parse the JSON response
                analysis = json.loads(response_text)
                
                # Validate and normalize the response
                if not isinstance(analysis, dict):
                    raise ValueError("Invalid response format")
                
                # Ensure required fields exist with meaningful defaults
                analysis.setdefault('is_suspicious', False)
                analysis.setdefault('risk_score', 0.0)
                analysis.setdefault('explanation', 'No analysis available')
                
                # Normalize risk_score
                try:
                    risk_score = float(analysis['risk_score'])
                    analysis['risk_score'] = max(0.0, min(1.0, risk_score))
                except (ValueError, TypeError):
                    analysis['risk_score'] = 0.0
                
                # Normalize is_suspicious based on risk_score
                if not isinstance(analysis['is_suspicious'], bool):
                    analysis['is_suspicious'] = analysis['risk_score'] > 0.7
                
                # Ensure explanation is detailed and meaningful
                if not analysis['explanation'] or len(analysis['explanation']) < 100:
                    # Generate a more detailed explanation based on the transaction
                    risk_factors = []
                    if amount > 10000:  # High amount threshold
                        risk_factors.append(f"unusually high amount (${amount})")
                    if location and "eastern europe" in location.lower():
                        risk_factors.append("suspicious location (Eastern Europe)")
                    if not category:
                        risk_factors.append("missing category information")
                    
                    if risk_factors:
                        analysis['explanation'] = (
                            f"Transaction analysis identified potential risk factors: {', '.join(risk_factors)}. "
                            f"The transaction amount of ${amount} in the {category or 'unspecified'} category "
                            f"from {location or 'unknown location'} requires additional verification."
                        )
                    else:
                        analysis['explanation'] = (
                            f"Transaction appears normal. Amount: ${amount}, Category: {category or 'Not specified'}, "
                            f"Location: {location or 'Not specified'}. No significant risk factors identified."
                        )
                
            except Exception as e:
                # Fallback analysis if API call fails
                risk_factors = []
                if amount > 10000:
                    risk_factors.append("high amount")
                if location and "eastern europe" in location.lower():
                    risk_factors.append("suspicious location")
                
                analysis = {
                    'is_suspicious': bool(risk_factors),
                    'risk_score': 0.7 if risk_factors else 0.2,
                    'explanation': (
                        f"Transaction analysis identified potential risk factors: {', '.join(risk_factors) if risk_factors else 'none'}. "
                        f"Amount: ${amount}, Category: {category or 'Not specified'}, "
                        f"Location: {location or 'Not specified'}. "
                        f"Please review the transaction details carefully."
                    )
                }
            
            # Update transaction
            transaction.is_suspicious = analysis['is_suspicious']
            transaction.save()
            
            # Create notification if suspicious
            if analysis['is_suspicious']:
                Notification.objects.create(
                    user=request.user,
                    transaction=transaction,
                    message=f"Suspicious transaction detected: {analysis['explanation']}"
                )
            
            return JsonResponse(analysis)
            
        except ValueError as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'An error occurred while processing the transaction.',
                'details': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    unread_notifications = notifications.filter(is_read=False)
    
    # Mark notifications as read
    unread_notifications.update(is_read=True)
    
    context = {
        'notifications': notifications
    }
    return render(request, 'core/notifications.html', context)

@login_required
def settings(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    if request.method == 'POST':
        try:
            risk_threshold = float(request.POST.get('risk_threshold', 70)) / 100
            notification_preferences = {
                'email': request.POST.get('email_notifications') == 'on',
                'push': request.POST.get('push_notifications') == 'on',
                'sms': request.POST.get('sms_notifications') == 'on'
            }
            
            user_profile.risk_threshold = risk_threshold
            user_profile.notification_preferences = notification_preferences
            user_profile.save()
            
            messages.success(request, 'Settings updated successfully!')
        except ValueError:
            messages.error(request, 'Invalid risk threshold value.')
        
        return redirect('settings')
    
    context = {
        'user_profile': user_profile
    }
    return render(request, 'core/settings.html', context)
