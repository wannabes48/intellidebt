from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Loan, Client, Reminder
from .forms import LoanForm, ClientForm, PaymentForm# You assume a ModelForm exists
from .ml_utils import ml_system
from django.db.models import Sum, Q
from datetime import date
from .ml_utils import ml_system
import json
from django.contrib import messages
from django.core.paginator import Paginator # For pagination
# In core/views.py

@login_required
def dashboard(request):
    total_loans = Loan.objects.count()
    active_defaults = Loan.objects.filter(status='Defaulted').count()

    #Search Logic
    query = request.GET.get('q')
    if query:
        # Search by Client Name OR Loan ID
        recent_loans = Loan.objects.select_related('client').filter(
            Q(client__name__icontains=query) | Q(id__icontains=query)
        ).order_by('-id')[:50] # Limit to 50 results
    else:
        # Default: Show recent 10
        recent_loans = Loan.objects.select_related('client').order_by('-id')[:10]
    
    # Get active loans with all the new fields
    active_loans = Loan.objects.select_related('client').filter(status__in=['Active', 'Defaulted'])
    recent_loans = Loan.objects.select_related('client').order_by('-id')[:10]
    active_loans_for_stats = Loan.objects.select_related('client').filter(status__in=['Active', 'Defaulted'])
    
    ml_input_data = []
    for loan in active_loans_for_stats:
        # Pass ALL the fields required by the ML model
        ml_input_data.append({
            'Age': loan.client.age,
            'Monthly_Income': loan.client.income,
            'Loan_Amount': loan.amount,
            'Loan_Tenure': loan.tenure,
            'Interest_Rate': loan.interest_rate,
            'Collateral_Value': loan.collateral_value,
            'Outstanding_Loan_Amount': loan.outstanding_amount,
            'Monthly_EMI': loan.monthly_emi,
            'Num_Missed_Payments': loan.missed_payments,
            'Days_Past_Due': loan.days_past_due
        })

    # The ML system will now use the real database data!
    segments = ml_system.get_client_segments(ml_input_data)
    
    segment_counts = {
        "Steady Repayer": segments.count("Steady Repayer"),
        "High Risk": segments.count("High Risk"),
        "Early Bird": segments.count("Early Bird"),
        # Add others if your ML model outputs them
        "Moderate Income, High Loan Burden": segments.count("Moderate Income, High Loan Burden"),
        "High Income, Low Default Risk": segments.count("High Income, Low Default Risk"),
        "Moderate Income, Medium Risk": segments.count("Moderate Income, Medium Risk"),
        "High Loan, Higher Default Risk": segments.count("High Loan, Higher Default Risk"),
    }
    
    # Clean up zero counts for cleaner chart
    segment_counts = {k: v for k, v in segment_counts.items() if v > 0}

    context = {
        'total_loans': total_loans,
        'active_defaults': active_defaults,
        'segment_data': json.dumps(segment_counts),
        'recent_loans': recent_loans,
        'query': query,
    }
    return render(request, 'dashboard.html', context)

@login_required
def create_loan(request):
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            
            # --- Objective A & C Integration: Predict Risk ---
            risk_prob = ml_system.predict_risk(
                loan.client.financial_score, 
                loan.amount, 
                loan.client.income
            )
            explanation = ml_system.explain_risk(
                loan.client.financial_score, 
                loan.amount, 
                loan.client.income
            )
            
            loan.predicted_default_risk = risk_prob
            loan.risk_explanation = explanation
            
            # Auto-flag as Default risk if probability > 70%
            if risk_prob > 0.7:
                # You might add a flag or alert here
                pass
                
            loan.save()
            return redirect('dashboard')
    else:
        form = LoanForm()
    return render(request, 'loan_form.html', {'form': form})

def trigger_reminders(request):
    """
    Simulates a background cron job. 
    Checks for overdue payments and creates reminders.
    """
    overdue_loans = Loan.objects.filter(
        status='Active', 
        due_date__lt=date.today()
    )
    
    count = 0
    for loan in overdue_loans:
        Reminder.objects.create(
            loan=loan,
            message=f"Dear {loan.client.name}, your loan of {loan.amount} is overdue.",
            method="SMS"
        )
        count += 1
        
    return render(request, 'reminder_success.html', {'count': count})

@login_required
def analytics_view(request):
    # Get the full dataset from our ML system to visualize
    data_json = ml_system.get_analytics_json()
    
    context = {
        'analytics_data': data_json
    }
    return render(request, 'analytics.html', context)

@login_required
def create_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('create_loan') # Go straight to loan creation
    else:
        form = ClientForm()
    return render(request, 'client_form.html', {'form': form})

@login_required
def loan_detail(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    
    # Generate ML Explanation on the fly
    ml_features = {
        'Monthly_Income': loan.client.income,
        'Loan_Amount': loan.amount,
        'Loan_Tenure': loan.tenure,
        'Num_Missed_Payments': loan.missed_payments,
        'Collateral_Value': loan.collateral_value
    }
    explanation = ml_system.explain_prediction(ml_features)
    
    context = {
        'loan': loan,
        'explanation': explanation
    }
    return render(request, 'loan_detail.html', context)

def trigger_reminders(request):
    """
    Simulates sending emails/SMS to clients with overdue loans.
    """
    print("------------------------------------------------")
    print("STARTING AUTOMATED REMINDER JOB...")
    
    # 1. Find overdue loans (Active status AND due date is before today)
    overdue_loans = Loan.objects.filter(
        status='Active', 
        due_date__lt=date.today()
    )
    
    count = 0
    for loan in overdue_loans:
        # 2. Simulate the Email/SMS Logic
        message = (
            f"URGENT: Dear {loan.client.name}, your loan payment of "
            f"${loan.outstanding_amount} was due on {loan.due_date}. "
            f"Please pay immediately."
        )
        
        # Print to Console (Simulating an email server)
        print(f" [SENDING EMAIL] To: {loan.client.contact} | Body: {message}")
        
        # 3. Log it in the database
        Reminder.objects.create(
            loan=loan,
            message=message,
            method="Email"
        )
        count += 1
        
    print(f"JOB COMPLETE: Sent {count} reminders.")
    print("------------------------------------------------")
        
    return render(request, 'reminder_success.html', {'count': count})

@login_required
def add_payment(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.loan = loan
            payment.save()
            
            # --- Business Logic: Update Loan Balance ---
            loan.outstanding_amount -= payment.amount
            
            # Prevent negative balance
            if loan.outstanding_amount <= 0:
                loan.outstanding_amount = 0
                loan.status = 'Paid'
                messages.success(request, "Loan fully paid off!")
            else:
                messages.success(request, f"Payment of ${payment.amount} recorded.")
                
            loan.save()
            return redirect('loan_detail', loan_id=loan.id)
    else:
        form = PaymentForm()
    
    return render(request, 'add_payment.html', {'form': form, 'loan': loan})

# In core/views.py

@login_required
def generate_settlement(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    
    # 1. Check if eligible (Only active/defaulted loans with high risk)
    if loan.status == 'Paid':
        messages.warning(request, "This loan is already paid.")
        return redirect('loan_detail', loan_id=loan.id)
        
    risk_score = loan.predicted_default_risk if loan.predicted_default_risk else 0.0
    
    # 2. Smart Calculation Logic
    if risk_score > 0.75:
        # High Risk: We are desperate. Offer 30% discount.
        discount_percent = 30
        reason = "High risk of total default. Aggressive offer generated."
    elif risk_score > 0.50:
        # Medium Risk: Offer 15% discount.
        discount_percent = 15
        reason = "Moderate risk. Incentive provided for immediate payment."
    else:
        # Low Risk: No discount recommended.
        messages.info(request, "Customer risk is low. No settlement recommended.")
        return redirect('loan_detail', loan_id=loan.id)
        
    # Calculate amounts
    discount_amount = (loan.outstanding_amount * discount_percent) / 100
    settlement_amount = loan.outstanding_amount - discount_amount
    
    context = {
        'loan': loan,
        'discount_percent': discount_percent,
        'discount_amount': discount_amount,
        'settlement_amount': settlement_amount,
        'reason': reason,
        'date': date.today()
    }
    return render(request, 'settlement_offer.html', context)

@login_required
def loan_list(request):
    # 1. Base Query
    loans = Loan.objects.select_related('client').order_by('-id')
    
    # 2. Filtering Logic
    status_filter = request.GET.get('status')
    if status_filter:
        loans = loans.filter(status=status_filter)
        
    risk_filter = request.GET.get('risk')
    if risk_filter == 'high':
        loans = loans.filter(predicted_default_risk__gt=0.5)
    elif risk_filter == 'low':
        loans = loans.filter(predicted_default_risk__lte=0.5)

    # 3. Pagination (Get per_page from settings or default to 10)
    per_page = request.session.get('ui_items_per_page', 10)
    paginator = Paginator(loans, per_page) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'risk_filter': risk_filter
    }
    return render(request, 'loan_list.html', context)

@login_required
def settings_view(request):
    if request.method == 'POST':
        # Save settings to User Session (Simple & Effective)
        theme = request.POST.get('theme')
        items_per_page = int(request.POST.get('items_per_page'))
        
        request.session['ui_theme'] = theme
        request.session['ui_items_per_page'] = items_per_page
        messages.success(request, "Settings saved successfully!")
        
    # Get current settings
    current_theme = request.session.get('ui_theme', 'light')
    current_per_page = request.session.get('ui_items_per_page', 10)
    
    return render(request, 'settings.html', {
        'current_theme': current_theme, 
        'current_per_page': current_per_page
    })