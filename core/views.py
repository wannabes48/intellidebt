from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, permission_required
from .models import Loan, Client, Reminder, CollectionLog, Payment
from .forms import LoanForm, ClientForm, PaymentForm# You assume a ModelForm exists
from django.db.models import Sum, Q, Count
from datetime import date
from .ml_utils import ml_system
from datetime import date
import json
from django.contrib import messages
from django.core.paginator import Paginator # For pagination
import plotly.express as px
import plotly.graph_objects as go
from django.utils import timezone
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import pandas as pd
import plotly.express as px
import csv
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from django.contrib.auth.decorators import login_required, permission_required
# In core/views.py

# In core/views.py

@login_required
def dashboard(request):
    # 1. Standard Stats
    total_loans = Loan.objects.count()
    active_defaults = Loan.objects.filter(
        Q(status='Defaulted') | 
        Q(status='Active', days_past_due__gt=0)
    ).count()
    active_loans_count = Loan.objects.filter(status='Active').count()
    total_disbursed = Loan.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # 2. Search Logic
    query = request.GET.get('q', '').strip()
    search_results = None # Variable to hold multiple results for the table
    recent_loans = None # Default to empty list if no query is provided

    if query:
        # If searching, find up to 20 matches by Name, ID, or Phone Number
        search_results = Loan.objects.select_related('client').filter(
            Q(client__name__icontains=query) | 
            Q(id__icontains=query) |
            Q(client__phone_number__icontains=query)
        ).order_by('-id')[:20]
    else:
        # If not searching, just show the 10 most recent loans
        recent_loans = Loan.objects.select_related('client').order_by('-id')[:10]

    status_counts = Loan.objects.values('status').annotate(count=Count('status'))
    status_data = {item['status']: item['count'] for item in status_counts}

    
    ml_input_data = [{'Age': l.client.age, 'Monthly_Income': l.client.monthly_income, 'Loan_Amount': l.amount, 'Loan_Tenure': l.tenure, 'Interest_Rate': l.interest_rate, 'Collateral_Value': l.collateral_value, 'Outstanding_Loan_Amount': l.amount, 'Monthly_EMI': l.monthly_emi, 'Num_Missed_Payments': l.missed_payments, 'Days_Past_Due': l.days_past_due} for l in Loan.objects.filter(status__in=['Active', 'Defaulted']).select_related('client')]
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
        'active_loans_count': active_loans_count,
        'total_disbursed': total_disbursed,
        'segment_data': json.dumps(segment_counts),
        'status_data': json.dumps(status_data),
        'recent_loans': recent_loans,
        'query': query,
        'search_results': search_results,
    }
    return render(request, 'dashboard.html', context)

@login_required
def create_loan(request):
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            
            if loan.tenure > 0:
                # Flat Rate Calculation (Principal + Total Interest) / Tenure
                # Note: We cast to float to ensure accurate decimal math
                amount = float(loan.amount)
                rate = float(loan.interest_rate) / 100.0
                years = loan.tenure / 12.0
                
                total_interest = amount * rate * years
                loan.monthly_emi = (amount + total_interest) / loan.tenure
            else:
                loan.monthly_emi = 0
            
            loan.outstanding_amount = loan.amount
            loan.status = 'Active' # Default status
            
            # --- ML Prediction Logic ---
            ml_features = {
                'Age': loan.client.age,
                'Monthly_Income': loan.client.monthly_income,
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
                # NEW WAY: The Smart Threshold
                threshold = ml_system.get('custom_threshold', 0.50)
                df_input = pd.DataFrame([ml_features])[ml_system.features_list]
                risk_probability = ml_system.classifier.predict_proba(df_input)[0][1]
                predicted_default_risk = 1 if risk_probability >= threshold else 0
                
                explanation = ml_system.explain_prediction(ml_features)
                
                loan.predicted_default_risk = predicted_default_risk
                loan.risk_percentage = risk_probability * 100
                loan.risk_explanation = ", ".join(explanation)
            except Exception as e:
                # Fallback if ML fails
                print(f"ML Error: {e}")
                loan.predicted_default_risk = 0.5
                loan.risk_percentage = 50.0
                loan.risk_explanation = "Manual Review Required (ML Error)"

            loan.save()
            messages.success(request, f"Loan Created! Risk Assessment: {'Risky' if loan.predicted_default_risk == 1 else 'Low Risk'}")
            return redirect('dashboard')
        else:
            # Debugging: Print errors to console so you can see them
            print("FORM ERRORS:", form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = LoanForm()
    return render(request, 'loan_form.html', {'form': form})



@login_required
def analytics_view(request):
    # 1. Grab the live dataframe from your loaded ML System
    df = ml_system.df_data
    
    # 2. Build the Plotly Figure
    fig = px.histogram(
        df, 
        x="Payment_History", 
        color="Recovery_Status", 
        barmode="group",
        title="How Payment History Affects Loan Recovery Status",
        labels={"Payment_History": "Payment History", "count": "Number of Loans"},
        color_discrete_map={
            "Fully Recovered": "#198754",     # Green
            "Partially Recovered": "#ffc107", # Yellow
            "Pending": "#dc3545"              # Red
        }
    )

    fig.update_layout(
        xaxis_title="Payment History",
        yaxis_title="Number of Loans",
        legend_title="Recovery Status",
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20) # Makes it fit nicely in a card
    )

    # 3. Convert the figure to an HTML/JS string (full_html=False ensures it just outputs the div)
    payment_history_chart = fig.to_html(full_html=False)


    fig2 = px.histogram(df, x='Loan_Amount', nbins=30, marginal="violin", opacity=0.7,
                       title="Loan Amount Distribution & Relationship with Monthly Income",
                       labels={'Loan_Amount': "Loan Amount", 'Monthly_Income': "Monthly Income"},
                       color_discrete_sequence=["royalblue"])

    # Safely extract the density curve data
    density_hist = px.histogram(df, x='Loan_Amount', nbins=30, histnorm='probability density')
    density_y = density_hist.data[0]['y']
    density_x = density_hist.data[0]['x'] # Use matching bins for X axis to prevent crashes

    fig2.add_trace(go.Scatter(
        x=density_x,
        y=density_y,
        mode='lines',
        name='Density Curve',
        line=dict(color='red', width=2)
    ))

    # Add the scatter plot
    scatter = px.scatter(df, x='Loan_Amount', y='Monthly_Income',
                         color='Loan_Amount', color_continuous_scale='Viridis',
                         size='Loan_Amount', hover_name=df.index)

    for trace in scatter.data:
        fig2.add_trace(trace)

    fig2.update_layout(
        annotations=[
            dict(
                x=max(df['Loan_Amount']) * 0.8, y=max(df['Monthly_Income']),
                text="Higher Loan Amounts are linked to Higher Income Levels",
                showarrow=True,
                arrowhead=2,
                font=dict(size=12, color="red")
            )
        ],
        xaxis_title="Loan Amount (in KES)",
        yaxis_title="Monthly Income (in KES)",
        template="plotly_white",
        showlegend=True,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    loan_income_chart = fig2.to_html(full_html=False)

    fig3 = px.box(
        df, 
        x="Recovery_Status", 
        y="Num_Missed_Payments",
        title="How Missed Payments Affect Loan Recovery Status",
        labels={"Recovery_Status": "Recovery Status", "Num_Missed_Payments": "Number of Missed Payments"},
        color="Recovery_Status",
        color_discrete_map={
            "Fully Recovered": "#198754",     # Green
            "Partially Recovered": "#ffc107", # Yellow
            "Pending": "#dc3545"              # Red
        },
        points="all" # Shows all the individual data points next to the box!
    )
    
    fig3.update_layout(
        xaxis_title="Recovery Status",
        yaxis_title="Number of Missed Payments",
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False # Hide legend since the x-axis already labels the colors perfectly
    )
    
    missed_payments_chart = fig3.to_html(full_html=False)

    clustering_features = ['Monthly_Income', 'Loan_Amount']
    X_cluster = ml_system.cluster_scaler.transform(df[clustering_features])
    df['Borrower_Segment'] = ml_system.kmeans.predict(X_cluster)
    
    # 2. Map the segment numbers to your descriptive names
    df['Segment_Name'] = df['Borrower_Segment'].map(ml_system.segment_map)

    # 3. Build the plot using Segment_Name for the colors
    fig4 = px.scatter(
        df, 
        x='Monthly_Income', 
        y='Loan_Amount',
        color='Segment_Name', 
        size='Loan_Amount',
        hover_data={'Monthly_Income': True, 'Loan_Amount': True, 'Segment_Name': True},
        title="Borrower Segments Based on Monthly Income and Loan Amount",
        labels={
            "Monthly_Income": "Monthly Income (KES)", 
            "Loan_Amount": "Loan Amount (KES)", 
            "Segment_Name": "Segment"
        },
        color_discrete_sequence=px.colors.qualitative.Vivid
    )

    fig4.add_annotation(
        x=df['Monthly_Income'].mean(), y=df['Loan_Amount'].max(),
        text="Higher loans are clustered in specific income groups",
        showarrow=True,
        arrowhead=2,
        font=dict(size=12, color="red")
    )

    fig4.update_layout(
        xaxis_title="Monthly Income (KES)",
        yaxis_title="Loan Amount (KES)",
        template="plotly_white",
        legend_title="Borrower Segment",
        margin=dict(l=20, r=20, t=50, b=20)
    )

    kmeans_chart = fig4.to_html(full_html=False)
    
    context = {
        # Pass the HTML chart directly to the template
        'payment_history_chart': payment_history_chart,
        'loan_income_chart': loan_income_chart,
        'missed_payments_chart': missed_payments_chart,
        'kmeans_chart': kmeans_chart
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
    # FIX 1: Use pk=loan_id to search by the database ID instead of the string LN_ID
    loan = get_object_or_404(Loan, pk=loan_id)
    client = loan.client

    safe_income = loan.client.monthly_income if loan.client.monthly_income > 0 else 1
    safe_collateral = loan.collateral_value if loan.collateral_value > 0 else 1
    missed_payments = loan.missed_payments if hasattr(loan, 'missed_payments') else 0
    days_late = loan.days_past_due if hasattr(loan, 'days_past_due') else 0

    if loan.status == 'Paid' or loan.outstanding_amount <= 0:
        # Hardcode the perfect score for closed loans
        risk_score = 0.0
        risk_percentage = 0.0
        threshold_percentage = int(ml_system.get('custom_threshold', 0.50) * 100)
        explanation = ["Loan has been fully repaid. Zero risk."]
        recommendation = "Loan Closed. No further action required. Good job!"
        
        # Ensure the database matches this perfect state
        if loan.predicted_default_risk != 0.0:
            loan.predicted_default_risk = 0.0
            loan.risk_percentage = 0.0
            loan.save()
    
    else:
    # Generate ML Explanation on the fly
        ml_features = {
            'Age': loan.client.age,
            'Monthly_Income': float(loan.client.monthly_income),
            'Loan_Amount': float(loan.amount),
            'Loan_Tenure': loan.tenure,
            'Interest_Rate': float(loan.interest_rate),
            'Collateral_Value': float(loan.collateral_value),
            'Outstanding_Loan_Amount': float(loan.outstanding_amount), 
            'Monthly_EMI': float(loan.monthly_emi),
            'Num_Missed_Payments': loan.missed_payments if hasattr(loan, 'missed_payments') else 0,
            'Days_Past_Due': loan.days_past_due if hasattr(loan, 'days_past_due') else 0,

            # --- THE 3 NEW REQUIRED FEATURES ---
            'DTI_Ratio': float(loan.monthly_emi) / float(safe_income),
            'Loan_to_Collateral': float(loan.outstanding_amount) / float(safe_collateral),
            'Payment_Strain': float(days_late) * float(loan.monthly_emi)
        }
        try:
            # NEW WAY: The Smart Threshold
            threshold = ml_system.get('custom_threshold', 0.50)
            df_input = pd.DataFrame([ml_features])[ml_system.features_list]
            risk_probability = ml_system.classifier.predict_proba(df_input)[0][1]
            risk_score = 1 if risk_probability >= threshold else 0
            
            explanation = ml_system.explain_prediction(ml_features)
            recommendation = ml_system.recommend_channel(risk_probability, days_late, loan.outstanding_amount)['action']
    
            # ==========================================
            # NEW: Format for the UI
            # ==========================================
            risk_percentage = round(risk_probability * 100, 1)
            threshold_percentage = int(threshold * 100) 

            loan.predicted_default_risk = risk_score
            loan.risk_percentage = risk_percentage
            loan.risk_explanation = ", ".join(explanation)
            loan.save()
        except Exception as e:
            print(f"ML Error in loan_detail view: {e}")
            risk_score = loan.predicted_default_risk
            explanation = [[loan.risk_explanation]]
            recommendation = "Manual Review Required (ML Error)"
            risk_percentage = loan.risk_percentage if loan.risk_percentage else round(risk_score * 100, 1)
            threshold_percentage = 50
    
    # Safely get logs just in case the related_name differs
    try:
        logs = CollectionLog.objects.filter(loan=loan).order_by('-id')
    except AttributeError:
        logs = CollectionLog.objects.filter(loan=loan).order_by('-id')
    
    other_loans = Loan.objects.filter(client=client).exclude(id=loan.id).order_by('-id')

    try:
        # Assuming your related_name is 'reminders'
        reminders = Reminder.objects.filter(loan=loan).order_by('-id')
    except AttributeError:
        # Fallback if you didn't set a related_name in models.py
        reminders = Reminder.objects.filter(loan=loan).order_by('-id')

    # ==========================================
    # NEW: Fetch Transaction History (Payments)
    # ==========================================
    try:
        # Tries to fetch using a custom related_name if you set one in models.py
        transactions = Payment.objects.filter(loan=loan).order_by('-id')
    except AttributeError:
        # Fallback if you didn't use a related_name
        transactions = Payment.objects.filter(loan=loan).order_by('-id')

    context = {
        'loan': loan,
        'risk_score_display': round(risk_score, 2),
        'risk_percentage': risk_percentage,
        'threshold_percentage': threshold_percentage,
        'explanation': explanation,
        'recommendation': recommendation,
        'logs': logs,
        'other_loans': other_loans,
        'reminders': reminders,
        'transactions': transactions,
    }
    return render(request, 'loan_detail.html', context)

@login_required
def log_interaction(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        channel = request.POST.get('channel')
        notes = request.POST.get('notes')
        
        CollectionLog.objects.create(
            loan=loan,
            method=channel,
            notes=notes
        )
        messages.success(request, "Interaction logged successfully.")
    return redirect('loan_detail', loan_id=loan.id)

def trigger_reminders(request):
    """
    Simulates sending emails/SMS to clients with overdue loans.
    """
    print("------------------------------------------------")
    print("STARTING AUTOMATED REMINDER JOB...")
    
    # 1. Find overdue loans (Active status AND due date is before today)
    overdue_loans = Loan.objects.filter(
        status='Active', 
        days_past_due__gt=0
    )
    
    count = 0
    for loan in overdue_loans:
        # 2. Simulate the Email/SMS Logic
        message = (
            f"URGENT: Dear {loan.client.name}, your loan payment of "
            f"KES {loan.outstanding_amount} is overdue by {loan.days_past_due} days. "
            f"Please pay immediately."
        )
        
        # Print to Console (Simulating an email server)
        print(f" [SENDING EMAIL] To: {loan.client.phone_number} | Body: {message}")
        
        # 3. Log it in the database
        Reminder.objects.create(
            loan=loan,
            message=message,
            scheduled_date=timezone.now()
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
            # Extract the exact amount the user is trying to pay
            attempted_payment = float(form.cleaned_data['amount_paid'])
            current_balance = float(loan.outstanding_amount)
            
            # ==========================================
            # THE EDGE CASE FIX: Prevent Overpayment
            # ==========================================
            if attempted_payment > current_balance:
                messages.error(
                    request, 
                    f"Transaction Failed: You entered KES {attempted_payment:.2f}, but the client only owes KES {current_balance:.2f}."
                )
                # Re-render the form immediately so they can fix the typo
                return render(request, 'add_payment.html', {'form': form, 'loan': loan})
            
            payment = form.save(commit=False)
            payment.loan = loan
            payment.save()
            
            # 1. Update Financials
            loan.outstanding_amount = current_balance - attempted_payment

            # Calculate the engineered features safely
            safe_income = loan.client.monthly_income if loan.client.monthly_income > 0 else 1
            safe_collateral = loan.collateral_value if loan.collateral_value > 0 else 1
            missed_payments = loan.missed_payments if hasattr(loan, 'missed_payments') else 0
            days_late = loan.days_past_due if hasattr(loan, 'days_past_due') else 0
            
            # 2. Check for Full Payment
            if loan.outstanding_amount <= 0:
                loan.outstanding_amount = 0
                loan.status = 'Paid'
                loan.predicted_default_risk = 0.0
                loan.risk_percentage = 0.0
                loan.risk_explanation = "Loan has been fully repaid. Zero risk."
                messages.success(request, "Payment recorded. Loan is now fully PAID!")
            else:
                # 3. AI RE-EVALUATION
                ml_features = {
                    'Age': loan.client.age,
                    'Monthly_Income': loan.client.monthly_income,
                    'Loan_Amount': loan.amount,
                    'Loan_Tenure': loan.tenure,
                    'Interest_Rate': loan.interest_rate,
                    'Collateral_Value': loan.collateral_value,
                    # --- FIX: Use the NEW outstanding amount ---
                    'Outstanding_Loan_Amount': loan.outstanding_amount, 
                    # -------------------------------------------
                    'Monthly_EMI': loan.monthly_emi,
                    'Num_Missed_Payments': loan.missed_payments,
                    'Days_Past_Due': loan.days_past_due,

                    # --- THE 3 NEW REQUIRED FEATURES ---
                    'DTI_Ratio': float(loan.monthly_emi) / float(safe_income),
                    'Loan_to_Collateral': float(loan.outstanding_amount) / float(safe_collateral),
                    'Payment_Strain': float(days_late) * float(loan.monthly_emi)
                }

                try:
                    # NEW WAY: The Smart Threshold
                    threshold = ml_system.get('custom_threshold', 0.50)
                    df_input = pd.DataFrame([ml_features])[ml_system.features_list]
                    risk_probability = ml_system.classifier.predict_proba(df_input)[0][1]
                    new_risk = 1 if risk_probability >= threshold else 0

                    loan.predicted_default_risk = new_risk
                    loan.risk_percentage = risk_probability * 100
                    new_explanation_list = ml_system.explain_prediction(ml_features)
                    loan.risk_explanation = ", ".join(new_explanation_list)
                except Exception as e:
                    print(f"ML Error during payment update: {e}")

            loan.save()
                
            messages.success(request, f"Payment of KES {payment.amount_paid} recorded. New Risk Score: {loan.predicted_default_risk:.2f}")
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
    loans = Loan.objects.select_related('client').all().order_by('-id') # Newest first
    
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
        # Safely filter assuming the field exists
        loans = loans.filter(predicted_default_risk__gt=0.5)
    elif risk_filter == 'low':
        loans = loans.filter(predicted_default_risk__lte=0.5)

    # 4. ONE SINGLE PAGINATION BLOCK (Removed the duplicate that erased your scores)
    per_page = request.session.get('ui_items_per_page', 20)
    paginator = Paginator(loans, per_page) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 5. Attach display helpers
    for loan in page_obj:
        # Check if the loan is closed/paid
        if loan.status == 'Paid' or loan.outstanding_amount <= 0:
            loan.risk_score_display = 0.0
            loan.risk_percentage = 0.0
            loan.risk_badge_color = "success"
            loan.risk_label = "Closed"
        elif loan.risk_percentage is not None:
            loan.risk_score_display = round(loan.risk_percentage, 1) 
            
            # thresholds for badges (consistent with progress bar colors)
            if loan.risk_percentage >= 70:
                loan.risk_badge_color = "danger"
                loan.risk_label = "High Risk"
            elif loan.risk_percentage >= 40:
                loan.risk_badge_color = "warning"
                loan.risk_label = "Medium Risk"
            else:
                loan.risk_badge_color = "success"
                loan.risk_label = "Low Risk"
        else:
            loan.risk_score_display = "N/A"
            loan.risk_badge_color = "light"
            loan.risk_label = "Pending"
            
    context = {
        'loans': page_obj, 
        'page_obj': page_obj,
        'query': query,
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
            Q(phone_number__icontains=query) |
            Q(email__icontains=query) |
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
@permission_required('core.delete_client', raise_exception=True)
def delete_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    
    if request.method == 'POST':
        client.delete()
        messages.success(request, f"Client '{client.name}' and all associated loans deleted.")
        return redirect('client_list')
    
    return render(request, 'confirm_delete.html', {'object': client, 'type': 'Client'})

@login_required
@permission_required('core.delete_loan', raise_exception=True)
def delete_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    # Optional: Prevent deleting paid loans for auditing purposes
    if loan.status == 'Paid':
        messages.error(request, "Security Block: Paid loans cannot be deleted, only archived.")
        return redirect('loan_detail', loan_id=loan.id)
        
    if request.method == 'POST':
        loan.delete()
        messages.success(request, "Loan record permanently deleted.")
        return redirect('loan_list') # Redirect to wherever your loans are listed
    return render(request, 'confirm_delete.html', {'object': loan, 'type': 'Loan'})

@login_required
def model_performance_view(request):
    # ==========================================
    # 1. FEATURE IMPORTANCE CHART
    # ==========================================
    # Extract what the AI thinks is most important directly from the model
    importances = ml_system.classifier.feature_importances_
    features = ml_system.features_list
    
    # Create a DataFrame and sort it
    feature_df = pd.DataFrame({'Feature': features, 'Importance': importances})
    feature_df = feature_df.sort_values(by='Importance', ascending=True)
    
    fig_importance = px.bar(
        feature_df, x='Importance', y='Feature', orientation='h',
        title='Random Forest Feature Importance',
        labels={'Importance': 'Impact on Risk Score', 'Feature': 'Loan Factor'},
        color='Importance',
        color_continuous_scale='Viridis'
    )
    fig_importance.update_layout(template='plotly_white', margin=dict(l=20, r=20, t=50, b=20))
    importance_chart = fig_importance.to_html(full_html=False)

    # ==========================================
    # 2. REAL-TIME ACCURACY EVALUATION
    # ==========================================
    loans = Loan.objects.all()
    y_true = []
    y_pred = []
    
    for loan in loans:
        # Determine GROUND TRUTH (What actually happened)
        # If they missed a payment or are > 15 days late, they are truly High Risk (1)
        true_risk = 1 if (getattr(loan, 'days_past_due', 0) > 15 or getattr(loan, 'missed_payments', 0) >= 1) else 0
        
        # Determine PREDICTION (What the AI guessed)
        threshold = ml_system.get('custom_threshold', 0.50)
        pred_risk = 1 if loan.predicted_default_risk >= threshold else 0
        
        y_true.append(true_risk)
        y_pred.append(pred_risk)

    # Calculate Metrics safely (zero_division=0 prevents crashes if no one has defaulted yet)
    if y_true:
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
        
        # Generate Confusion Matrix
        cm = confusion_matrix(y_true, y_pred)
        fig_cm = px.imshow(
            cm, text_auto=True, 
            labels=dict(x="AI Predicted Label", y="Actual True Label", color="Count"),
            x=['Predicted Low Risk (0)', 'Predicted High Risk (1)'],
            y=['Actually Low Risk (0)', 'Actually High Risk (1)'],
            title="Real-Time Confusion Matrix",
            color_continuous_scale="Blues"
        )
        fig_cm.update_layout(template='plotly_white')
        cm_chart = fig_cm.to_html(full_html=False)
    else:
        precision = recall = f1 = accuracy = 0
        cm_chart = "<div class='alert alert-warning'>Not enough loan data to generate matrix.</div>"

    context = {
        'importance_chart': importance_chart,
        'cm_chart': cm_chart,
        'precision': precision * 100,
        'recall': recall * 100,
        'f1': f1 * 100,
        'accuracy': accuracy * 100,
    }
    return render(request, 'model_performance.html', context)

@login_required
def clearance_certificate(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Security Check: Only allow certificates for fully paid loans
    if loan.status != 'Paid' or loan.outstanding_amount > 0:
        messages.error(request, "Denied: A Clearance Certificate can only be generated for fully repaid loans.")
        return redirect('loan_detail', loan_id=loan.id)
        
    context = {
        'loan': loan,
        'date_issued': timezone.now()
    }
    return render(request, 'clearance_certificate.html', context)

@login_required
def report_generation(request):
    # Determine the timeframe from the URL (e.g., ?period=weekly)
    period = request.GET.get('period', 'monthly') # Defaults to monthly
    today = timezone.now()
    
    if period == 'daily':
        start_date = today - timedelta(days=1)
        title = "Daily Financial Report"
    elif period == 'weekly':
        start_date = today - timedelta(days=7)
        title = "Weekly Financial Report"
    else: # monthly
        start_date = today - timedelta(days=30)
        title = "Monthly Financial Report"

    # Fetch data within that timeframe
    new_loans = Loan.objects.filter(created_at__gte=start_date)
    recent_payments = Payment.objects.filter(payment_date__gte=start_date)
    
    # Calculate Metrics
    total_disbursed = sum(loan.amount for loan in new_loans)
    total_collected = sum(payment.amount_paid for payment in recent_payments)
    
    # CSV Export Logic
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Intellidebt_{period}_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Report Type', title])
        writer.writerow(['Generated On', today.strftime("%Y-%m-%d %H:%M")])
        writer.writerow([])
        writer.writerow(['Metric', 'Value (KES)'])
        writer.writerow(['Total Disbursed', total_disbursed])
        writer.writerow(['Total Collected', total_collected])
        writer.writerow(['New Loans Issued', new_loans.count()])
        
        return response

    context = {
        'title': title,
        'period': period,
        'total_disbursed': total_disbursed,
        'total_collected': total_collected,
        'loans_count': new_loans.count(),
        'payments_count': recent_payments.count(),
    }
    return render(request, 'reports.html', context)


# =============================================
# PUBLIC LANDING PAGE
# =============================================
def landing_page(request):
    """Public-facing landing page — no auth required."""
    return render(request, 'landing.html')


# =============================================
# CSV DATA INGESTION PIPELINE
# =============================================
from .ml_service import ml_system as ingestion_ml_system
from decimal import Decimal, InvalidOperation

@login_required
def upload_portfolio(request):
    """Admin-only CSV upload with instant ML risk scoring per row."""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff privileges required.")
        return redirect('dashboard')

    results = None

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Invalid file format. Only .csv files are accepted.")
            return redirect('upload_portfolio')

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            messages.error(request, f"Failed to parse CSV: {e}")
            return redirect('upload_portfolio')

        # Required columns check
        required_cols = ['Borrower_ID', 'Borrower_Name', 'Age', 'Monthly_Income',
                         'Loan_ID', 'Loan_Amount', 'Loan_Tenure', 'Interest_Rate',
                         'Monthly_EMI', 'Num_Missed_Payments', 'Days_Past_Due']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            messages.error(request, f"Missing required columns: {', '.join(missing)}")
            return redirect('upload_portfolio')

        # Fill optional columns with defaults
        df['Gender'] = df.get('Gender', pd.Series(['Unknown'] * len(df)))
        df['Collateral_Value'] = df.get('Collateral_Value', pd.Series([0] * len(df)))
        df['Employment_Type'] = df.get('Employment_Type', pd.Series(['Salaried'] * len(df)))
        df['Address'] = df.get('Address', pd.Series(['N/A'] * len(df)))
        df['Phone_Number'] = df.get('Phone_Number', pd.Series([''] * len(df)))
        df['Email'] = df.get('Email', pd.Series([''] * len(df)))
        df['Num_Dependents'] = df.get('Num_Dependents', pd.Series([0] * len(df)))
        df['Outstanding_Loan_Amount'] = df.get('Outstanding_Loan_Amount', df['Loan_Amount'])
        df['Recovery_Status'] = df.get('Recovery_Status', pd.Series(['Pending'] * len(df)))

        # Replace NaN with defaults
        df = df.fillna({
            'Gender': 'Unknown', 'Collateral_Value': 0, 'Employment_Type': 'Salaried',
            'Address': 'N/A', 'Phone_Number': '', 'Email': '', 'Num_Dependents': 0,
            'Outstanding_Loan_Amount': 0, 'Recovery_Status': 'Pending'
        })

        created_count = 0
        skipped_count = 0
        error_count = 0
        error_details = []
        loans_to_create = []

        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel row (header = row 1)
            try:
                # 1. Get or Create Client
                client_id = str(row['Borrower_ID']).strip()
                client, _ = Client.objects.get_or_create(
                    client_id=client_id,
                    defaults={
                        'name': str(row['Borrower_Name']).strip(),
                        'age': int(row['Age']),
                        'gender': str(row.get('Gender', 'Unknown')),
                        'monthly_income': Decimal(str(row['Monthly_Income'])),
                        'employment_type': str(row.get('Employment_Type', 'Salaried')),
                        'address': str(row.get('Address', 'N/A')),
                        'phone_number': str(row.get('Phone_Number', '')),
                        'email': str(row.get('Email', '')),
                        'num_dependents': int(row.get('Num_Dependents', 0)),
                    }
                )

                # 2. Check for duplicate loan
                loan_id = str(row['Loan_ID']).strip()
                if Loan.objects.filter(loan_id=loan_id).exists():
                    skipped_count += 1
                    continue

                # 3. Run ML Model for risk scoring
                ml_features = {
                    'Age': float(row['Age']),
                    'Monthly_Income': float(row['Monthly_Income']),
                    'Loan_Amount': float(row['Loan_Amount']),
                    'Loan_Tenure': float(row['Loan_Tenure']),
                    'Interest_Rate': float(row['Interest_Rate']),
                    'Collateral_Value': float(row.get('Collateral_Value', 0)),
                    'Outstanding_Loan_Amount': float(row.get('Outstanding_Loan_Amount', row['Loan_Amount'])),
                    'Monthly_EMI': float(row['Monthly_EMI']),
                    'Num_Missed_Payments': float(row['Num_Missed_Payments']),
                    'Days_Past_Due': float(row['Days_Past_Due']),
                }

                # NEW WAY: The Smart Threshold
                threshold = ingestion_ml_system.get('custom_threshold', 0.50)
                df_input_row = pd.DataFrame([ml_features])[ingestion_ml_system.features_list]
                risk_probability = ingestion_ml_system.classifier.predict_proba(df_input_row)[0][1]
                risk_score_binary = 1 if risk_probability >= threshold else 0
                
                explanation = ingestion_ml_system.explain_prediction(ml_features)

                # 4. Determine status from data
                days_past = int(row['Days_Past_Due'])
                missed = int(row['Num_Missed_Payments'])
                outstanding = Decimal(str(row.get('Outstanding_Loan_Amount', row['Loan_Amount'])))

                if outstanding <= 0:
                    status = 'Paid'
                elif days_past > 90 or missed > 5:
                    status = 'Defaulted'
                else:
                    status = 'Active'

                # 5. Build loan object
                loan = Loan(
                    loan_id=loan_id,
                    client=client,
                    amount=Decimal(str(row['Loan_Amount'])),
                    tenure=int(row['Loan_Tenure']),
                    interest_rate=Decimal(str(row['Interest_Rate'])),
                    collateral_value=Decimal(str(row.get('Collateral_Value', 0))),
                    outstanding_amount=outstanding,
                    monthly_emi=Decimal(str(row['Monthly_EMI'])),
                    missed_payments=missed,
                    days_past_due=days_past,
                    status=status,
                    recovery_status=str(row.get('Recovery_Status', 'Pending')),
                    predicted_default_risk=float(risk_score_binary),
                    risk_percentage=risk_probability * 100,
                    risk_explanation='; '.join(explanation) if explanation else "System Assessment Complete",
                )
                loans_to_create.append(loan)
                created_count += 1

            except (ValueError, InvalidOperation, KeyError) as e:
                error_count += 1
                error_details.append(f"Row {row_num}: {str(e)}")
                continue

        # Bulk create all valid loans
        if loans_to_create:
            Loan.objects.bulk_create(loans_to_create, ignore_conflicts=True)

        results = {
            'total_rows': len(df),
            'created': created_count,
            'skipped': skipped_count,
            'errors': error_count,
            'error_details': error_details[:20],  # Cap at 20 for display
        }
        messages.success(request, f"Portfolio upload complete: {created_count} loans created, {skipped_count} skipped.")

    return render(request, 'upload_portfolio.html', {'results': results})


def about_view(request):
    return render(request, 'about.html')


def contact_view(request):
    return render(request, 'contact_us.html')


def privacy_view(request):
    return render(request, 'privacy.html')


from django.http import JsonResponse

def chrome_devtools_json(request):
    """Serves the .well-known file to resolve DevTools 404 errors."""
    return JsonResponse({})

def terms_view(request):
    return render(request, 'terms.html')