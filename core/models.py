from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    pass

class Client(models.Model):
    # Demographics & Profile (Matches ML CSV)
    client_id = models.CharField(max_length=50, unique=True, help_text="e.g., BRW_1001")
    name = models.CharField(max_length=255)
    age = models.IntegerField(default=30)
    gender = models.CharField(max_length=20, default="Unknown")

    phone_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # Financial Standing
    employment_type = models.CharField(max_length=50, default="Salaried")
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    num_dependents = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.client_id})"

class Loan(models.Model):
    # Loan Details (Matches ML CSV)
    loan_id = models.CharField(max_length=50, unique=True, help_text="e.g., LN_1001")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    tenure = models.IntegerField(help_text="Tenure in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    loan_type = models.CharField(max_length=100, default="Personal")
    collateral_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    
    # Repayment Status
    outstanding_amount = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_emi = models.DecimalField(max_digits=15, decimal_places=2)
    payment_history = models.CharField(max_length=50, default="On-Time")
    missed_payments = models.IntegerField(default=0)
    days_past_due = models.IntegerField(default=0)
    
    # System Status
    status = models.CharField(max_length=50, default="Active") # Needed for your views
    recovery_status = models.CharField(max_length=50, default="Pending")
    
    # ML Fields
    predicted_default_risk = models.FloatField(default=0.0)
    risk_explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.loan_id} - {self.client.name}"

# --- TRANSACTIONAL TABLES (Required for your views to work) ---

class Payment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Payment of {self.amount_paid} for {self.loan.loan_id}"

class Reminder(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='reminders')
    message = models.TextField()
    scheduled_date = models.DateTimeField()
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder for {self.loan.loan_id} on {self.scheduled_date}"

class CollectionLog(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='collection_logs')
    method = models.CharField(max_length=100, help_text="Calls, Emails, Settlement Offer")
    legal_action_taken = models.CharField(max_length=10, default='No')
    attempt_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Attempt on {self.loan.loan_id} via {self.method}"