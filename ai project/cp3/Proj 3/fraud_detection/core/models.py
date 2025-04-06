from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_suspicious = models.BooleanField(default=False)
    location = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.timestamp}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Notification for {self.user.username} - {self.timestamp}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    notification_preferences = models.JSONField(default=dict)
    risk_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=0.7)
    last_analysis = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
