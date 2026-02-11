from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    pass

class Client(models.Model):
    # CSV: Borrower_ID maps to name (or we can add a specific ID field)
    name = models.CharField(max_length=255) 
    contact = models.CharField(max_length=50, default="Unknown")
    address = models.TextField(default="Unknown")
    
    # CSV: Monthly_Income
    income = models.FloatField(help_text="Monthly Income", default=0.0)
    
    # CSV: Age
    age = models.IntegerField(default=30)
    
    # CSV: Employment_Type
    employment_type = models.CharField(max_length=50, default="Salaried")
    
    # Legacy field (keep for compatibility, we will auto-generate it)
    financial_score = models.IntegerField(default=600, help_text="Credit Score (300-850)")

    def __str__(self):
        return f"{self.name} ({self.employment_type})"

class Loan(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Paid', 'Paid'), # Maps to 'Fully Recovered'
        ('Defaulted', 'Defaulted'), # Maps to 'Not Recovered'/'Partially Recovered'
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    # CSV Mapped Fields
    amount = models.FloatField(help_text="Loan Amount") # Loan_Amount
    interest_rate = models.FloatField() # Interest_Rate
    tenure = models.IntegerField(help_text="Months", default=12) # Loan_Tenure
    collateral_value = models.FloatField(default=0.0) # Collateral_Value
    outstanding_amount = models.FloatField(default=0.0) # Outstanding_Loan_Amount
    monthly_emi = models.FloatField(default=0.0) # Monthly_EMI
    missed_payments = models.IntegerField(default=0) # Num_Missed_Payments
    days_past_due = models.IntegerField(default=0) # Days_Past_Due
    
    # System fields
    due_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    predicted_default_risk = models.FloatField(null=True, blank=True)
    risk_explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.client.name} - ${self.amount}"

class Payment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    amount = models.FloatField()

class Reminder(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=10, default='SMS')

class CollectionLog(models.Model):
    CHANNEL_CHOICES = [
        ('SMS', 'SMS'),
        ('Email', 'Email'),
        ('Call', 'Phone Call'),
        ('Visit', 'Physical Visit'),
        ('Legal', 'Legal Action'),
    ]
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='logs')
    interaction_date = models.DateTimeField(auto_now_add=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    officer_notes = models.TextField()
    
    def __str__(self):
        return f"{self.channel} - {self.loan.client.name}"