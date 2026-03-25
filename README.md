A Smart Loan Recovery System
An end-to-end ML system that predicts loan defaults and creates personalized recovery strategies for borrowers.

Tools & Techniques used:
-Customer Segmentation and clustering
-Explainable AI (XAI) for transparent decisions



# 🚀 Intellidebt: Smart Loan Recovery System<br>

**Intellidebt** is a comprehensive, AI-driven Software-as-a-Service (SaaS) platform designed for microfinance institutions and Saccos. It transitions loan recovery from a reactive, manual process to a proactive, automated workflow. By leveraging machine learning, Intellidebt predicts default risks before they happen and automates targeted recovery interventions.<br>

## ✨ Core Features<br>

* **Predictive AI Risk Scoring:** Utilizes a custom-trained Random Forest classifier to analyze borrower data (including engineered features like Debt-to-Income ratio and Payment Strain) to predict default likelihood.<br>
* **Dynamic Risk Dashboards:** Displays exact risk probabilities with color-coded visual indicators, allowing loan admins to prioritize high-risk accounts instantly.<br>
* **Automated Smart Interventions:** Automatically triggers risk-based SMS and email reminders. Low-risk clients receive gentle nudges, while high-risk defaulters receive escalated warnings and dynamically generated PDF Settlement Offers.<br>
* **Seamless Data Ingestion Pipeline:** Allows administrators to bulk-upload legacy `.csv` loan portfolios. The Pandas-powered engine sanitizes data, imputes missing values, and runs real-time AI risk assessments on every row before database insertion.<br>
* **Enterprise-Grade Security (RBAC):** Strict Role-Based Access Control separates `Admin` and `Officer` privileges. Includes hard-stop warning interfaces to prevent accidental data deletion and robust transaction guardrails to block overpayment edge cases.<br>
* **Comprehensive Reporting:** Generates one-click Daily, Weekly, and Monthly financial summary reports exportable to CSV, complete with humanized currency formatting.<br>

## 🛠️ Technology Stack<br>

* **Backend:** Python 3.10, Django 4.2<br>
* **Machine Learning:** Scikit-Learn, Pandas, NumPy, Joblib<br>
* **Database:** PostgreSQL (hosted on Supabase)<br>
* **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript<br>
* **Deployment:** Render (Gunicorn)<br>

## 🧠 Machine Learning Architecture<br>

The predictive engine is powered by a `RandomForestClassifier` optimized via `GridSearchCV`. <br>
* **Feature Engineering:** Raw financial data is transformed into powerful predictive ratios (`DTI_Ratio`, `Loan_to_Collateral`, `Payment_Strain`).<br>
* **Threshold Tuning:** The decision boundary was manually adjusted from the default `0.50` to `0.40`. This strategic tuning sacrifices a negligible amount of precision to drastically improve the **Recall** rate, ensuring the system catches a significantly higher percentage of actual real-world defaulters.<br>

## 💻 Local Setup & Installation<br>

Follow these steps to run the Intellidebt environment on your local machine.<br>

**1. Clone the repository**<br>
```bash
git clone https://github.com/yourusername/intellidebt.git
cd intellidebt
```

**2. Set up a Virtual Environment**<br>
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

**3. Install Dependencies**<br>
```bash
pip install -r requirements.txt
```

**4. Environment Variables**<br>
Create a `.env` file in the root directory and add your Supabase database credentials and Django secret key:
```ini<br>
SECRET_KEY=your_django_secret_key
DEBUG=True
DATABASE_URL=postgres://user:password@aws-0-region.pooler.supabase.com:6543/postgres
```

**5. Apply Migrations**<br>
```bash
python manage.py makemigrations
python manage.py migrate
```

**6. Create a Superuser (Admin)**<br>
```bash
python manage.py createsuperuser
```

**7. Run the Development Server**<br>
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000` to access the Landing Page and Dashboard.<br>

## 🚀 Deployment Notes (Render)<br>

When deploying to Render, ensure the following environment variables are set in the Render dashboard:<br>
* `DEBUG = False`
* `WEB_CONCURRENCY = 1` *(Critical: Restricts Gunicorn to a single worker to prevent Out-Of-Memory (OOM) errors on free/hobby tiers due to the size of the Scikit-Learn models).*

## 🗄️ Backup & Recovery<br>

The system utilizes a hybrid backup mechanism:<br>
1.  **Infrastructure:** Automated daily snapshots via Supabase PostgreSQL.<br>
2.  **Application:** Administrators can generate manual JSON dumps of the core application state using Django's serialization tools:<br>
    ```bash
    python manage.py dumpdata core > intellidebt_backup.json
    ```

## 📄 License<br>
This project is licensed under the MIT License - see the LICENSE file for details.<br>
