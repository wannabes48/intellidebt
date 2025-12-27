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

# In core/views.py

@login_required
def dashboard(request):
    # 1. Standard Stats
    total_loans = Loan.objects.count()
    active_defaults = Loan.objects.filter(status='Defaulted').count()
    
    # 2. Search Logic
    query = request.GET.get('q')
    search_match = None  # Variable to hold the single result for the modal

    if query:
        # Search by Name or ID
        recent_loans = Loan.objects.select_related('client').filter(
            Q(client__name__icontains=query) | Q(id__icontains=query)
        ).order_by('-id')[:50]
        
        # If we find exactly one match (or you want to show the top match), grab it
        if recent_loans.exists():
            search_match = recent_loans.first() # Grab the top result for the "Window"
    else:
        recent_loans = Loan.objects.select_related('client').order_by('-id')[:10]

    # ... (Keep existing Analytics/Segmentation logic here) ...
    # (Copied from your previous code for segmentation)
    ml_input_data = [{'Age': l.client.age, 'Monthly_Income': l.client.income, 'Loan_Amount': l.amount, 'Loan_Tenure': l.tenure, 'Interest_Rate': l.interest_rate, 'Collateral_Value': l.collateral_value, 'Outstanding_Loan_Amount': l.amount, 'Monthly_EMI': l.monthly_emi, 'Num_Missed_Payments': l.missed_payments, 'Days_Past_Due': l.days_past_due} for l in Loan.objects.filter(status__in=['Active', 'Defaulted'])]
    segments = ml_system.get_client_segments(ml_input_data)
    segment_counts = {k: v for k, v in {
        "Steady Repayer": segments.count("Steady Repayer"),
        "High Risk": segments.count("High Risk"),
        "Early Bird": segments.count("Early Bird"),
        "Moderate Income, High Loan Burden": segments.count("Moderate Income, High Loan Burden"),
        "High Income, Low Default Risk": segments.count("High Income, Low Default Risk"),
        "Moderate Income, Medium Risk": segments.count("Moderate Income, Medium Risk"),
        "High Loan, Higher Default Risk": segments.count("High Loan, Higher Default Risk"),
    }.items() if v > 0}

    context = {
        'total_loans': total_loans,
        'active_defaults': active_defaults,
        'segment_data': json.dumps(segment_counts),
        'recent_loans': recent_loans,
        'query': query,
        'search_match': search_match, # <--- PASS THIS NEW VARIABLE
    }
    return render(request, 'dashboard.html', context)

@login_required
def create_loan(request):
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            
            # --- CRITICAL FIX: Set Initial Outstanding Amount ---
            # If this is missing, the DB might reject the save
            loan.outstanding_amount = loan.amount
            loan.status = 'Active' # Default status
            
            # --- ML Prediction Logic ---
            ml_features = {
                'Age': loan.client.age,
                'Monthly_Income': loan.client.income,
                'Loan_Amount': loan.amount,
                'Loan_Tenure': loan.tenure,
                'Interest_Rate': loan.interest_rate,
                'Collateral_Value': loan.collateral_value,
                'Outstanding_Loan_Amount': loan.amount, 
                'Monthly_EMI': (loan.amount / loan.tenure) if loan.tenure > 0 else 0,
                'Num_Missed_Payments': 0,
                'Days_Past_Due': 0
            }
            
            try:
                risk_prob, strategy = ml_system.predict_risk(ml_features)
                explanation = ml_system.explain_prediction(ml_features)
                
                loan.predicted_default_risk = risk_prob
                loan.risk_explanation = ", ".join(explanation)
            except Exception as e:
                # Fallback if ML fails, so we can still save the loan
                print(f"ML Error: {e}")
                loan.predicted_default_risk = 0.5
                loan.risk_explanation = "Manual Review Required (ML Error)"

            loan.save()
            messages.success(request, f"Loan Created! Risk Score: {loan.predicted_default_risk:.2f}")
            return redirect('dashboard')
        else:
            # Debugging: Print errors to console so you can see them
            print("FORM ERRORS:", form.errors)
            messages.error(request, "Please correct the errors below.")
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
    # 1. Start with all loans
    loans = Loan.objects.select_related('client').order_by('-id')
    
    # 2. SEARCH LOGIC (Name or ID)
    query = request.GET.get('q')
    if query:
        loans = loans.filter(
            Q(client__name__icontains=query) | 
            Q(id__icontains=query)
        )

    # 3. FILTER LOGIC (Status & Risk)
    status_filter = request.GET.get('status')
    if status_filter:
        loans = loans.filter(status=status_filter)
        
    risk_filter = request.GET.get('risk')
    if risk_filter == 'high':
        loans = loans.filter(predicted_default_risk__gt=0.5)
    elif risk_filter == 'low':
        loans = loans.filter(predicted_default_risk__lte=0.5)

    # 4. Pagination
    per_page = request.session.get('ui_items_per_page', 10)
    paginator = Paginator(loans, per_page) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query, # Pass back to template
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


@login_required
def client_list(request):
    # 1. Base Query
    clients = Client.objects.all().order_by('-id')
    
    # 2. Search Logic
    query = request.GET.get('q')
    if query:
        clients = clients.filter(
            Q(name__icontains=query) | 
            Q(contact__icontains=query) |
            Q(employment_type__icontains=query)
        )

    # 3. Pagination (Grid of 9 cards per page looks good)
    paginator = Paginator(clients, 9) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'client_list.html', context)

@login_required
def delete_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    
    if request.method == 'POST':
        client.delete()
        messages.success(request, f"Client '{client.name}' and all associated loans deleted.")
        return redirect('client_list')
    
    return render(request, 'confirm_delete.html', {'object': client, 'type': 'Client'})