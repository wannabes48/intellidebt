
import os
import time
import django
from django.conf import settings
from django.template.loader import render_to_string

# Setup Django (minimal)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

def fix_and_verify():
    file_path = os.path.abspath('core/templates/loan_list.html')
    print(f"Target file: {file_path}")

    # 1. FORCE DELETE
    if os.path.exists(file_path):
        print("File exists. Attempting to delete...")
        try:
            os.remove(file_path)
            print("File deleted successfully.")
        except Exception as e:
            print(f"ERROR: Could not delete file: {e}")
            return
    else:
        print("File does not exist (clean start).")

    # 2. WRITE CORRECT CONTENT
    correct_content = r"""{% extends 'base.html' %}
{# FIX APPLIED VIA SCRIPT #}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">All Loans Directory</h2>
</div>

<div class="card mb-4 border-0 shadow-sm">
    <div class="card-body bg-light rounded">
        <form method="get" class="row g-2">

            <div class="col-md-5">
                <div class="input-group">
                    <span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span>
                    <input type="text" name="q" class="form-control border-start-0"
                        placeholder="Search by Name or Loan ID..." value="{{ query|default:'' }}">
                </div>
            </div>

            <div class="col-md-3">
                <select name="status" class="form-select">
                    <option value="">Status: All</option>
                    <option value="Active" {% if status_filter == 'Active' %}selected{% endif %}>Active</option>
                    <option value="Defaulted" {% if status_filter == 'Defaulted' %}selected{% endif %}>Defaulted</option>
                    <option value="Paid" {% if status_filter == 'Paid' %}selected{% endif %}>Paid</option>
                </select>
            </div>
            <div class="col-md-3">
                <select name="risk" class="form-select">
                    <option value="">Risk: All</option>
                    <option value="high" {% if risk_filter == 'high' %}selected{% endif %}>High Risk (> 50%)</option>
                    <option value="low" {% if risk_filter == 'low' %}selected{% endif %}>Low Risk (< 50%)</option>
                </select>
            </div>

            <div class="col-md-1">
                <button type="submit" class="btn btn-primary w-100">Go</button>
            </div>
        </form>
    </div>
</div>

<div class="card shadow border-0">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>ID</th>
                        <th>Client</th>
                        <th>Amount</th>
                        <th>Tenure</th>
                        <th>Status</th>
                        <th>Risk Score</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for loan in page_obj %}
                    <tr>
                        <td><span class="badge bg-secondary">#{{ loan.id }}</span></td>
                        <td>
                            <strong>{{ loan.client.name }}</strong><br>
                            <small class="text-muted">{{ loan.client.contact }}</small>
                        </td>
                        <td>KES {{ loan.amount|stringformat:".2f" }}</td>
                        <td>{{ loan.tenure }} mths</td>
                        <td>
                            {% if loan.status == 'Active' %}
                            <span class="badge bg-primary bg-opacity-10 text-primary">Active</span>
                            {% elif loan.status == 'Defaulted' %}
                            <span class="badge bg-danger bg-opacity-10 text-danger">Defaulted</span>
                            {% else %}
                            <span class="badge bg-success bg-opacity-10 text-success">Paid</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if loan.predicted_default_risk %}
                            {% if loan.predicted_default_risk > 0.75 %}
                            <div class="progress" style="height: 6px; width: 80px;">
                                <div class="progress-bar bg-danger"
                                    style="width: {{ loan.predicted_default_risk|stringformat:'.2f'|slice:'2:' }}%">
                                </div>
                            </div>
                            <small class="text-danger fw-bold">{{ loan.predicted_default_risk|stringformat:".2f"
                                }}</small>
                            {% elif loan.predicted_default_risk >= 0.50 %}
                            <div class="progress" style="height: 6px; width: 80px;">
                                <div class="progress-bar bg-warning"
                                    style="width: {{ loan.predicted_default_risk|stringformat:'.2f'|slice:'2:' }}%">
                                </div>
                            </div>
                            <small class="text-warning fw-bold">{{ loan.predicted_default_risk|stringformat:".2f"
                                }}</small>
                            {% else %}
                            <div class="progress" style="height: 6px; width: 80px;">
                                <div class="progress-bar bg-success"
                                    style="width: {{ loan.predicted_default_risk|stringformat:'.2f'|slice:'2:' }}%">
                                </div>
                            </div>
                            <small class="text-success">{{ loan.predicted_default_risk|stringformat:".2f" }}</small>
                            {% endif %}
                            {% else %}
                            -
                            {% endif %}
                        </td>
                        <td>
                            <a href="{% url 'loan_detail' loan.id %}" class="btn btn-sm btn-outline-primary">View</a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="7" class="text-center py-4 text-muted">No loans found matching your criteria.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <div class="card-footer bg-white d-flex justify-content-between align-items-center">
        <small class="text-muted">Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</small>
        <nav>
            <ul class="pagination pagination-sm mb-0">
                {% if page_obj.has_previous %}
                <li class="page-item"><a class="page-link"
                        href="?page={{ page_obj.previous_page_number }}&q={{ query|default:'' }}&status={{ status_filter|default:'' }}&risk={{ risk_filter|default:'' }}">&laquo;</a>
                </li>
                {% endif %}

                {% if page_obj.has_next %}
                <li class="page-item"><a class="page-link"
                        href="?page={{ page_obj.next_page_number }}&q={{ query|default:'' }}&status={{ status_filter|default:'' }}&risk={{ risk_filter|default:'' }}">&raquo;</a>
                </li>
                {% endif %}
            </ul>
        </nav>
    </div>
</div>
{% endblock %}"""

    print("Writing new content...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(correct_content)
        print("Write successful.")
    except Exception as e:
         print(f"ERROR: Could not write file: {e}")
         return

    # 3. VERIFY CONTENT ON DISK
    print("Verifying content on disk...")
    with open(file_path, 'r', encoding='utf-8') as f:
        read_content = f.read()
        if "{# FIX APPLIED VIA SCRIPT #}" in read_content:
            print("  [OK] New comment found.")
        else:
            print("  [FAIL] New comment NOT found.")
        
        if "status_filter == 'Active'" in read_content:
            print("  [OK] Correct syntax found (spaces present).")
        else:
            print("  [FAIL] Incorrect syntax found (no spaces?).")
            print("snippet:", read_content[600:800]) # approximate location

    # 4. RUN VERIFY_LOAN_LIST from here (logic wise)
    print("Attempting to run verification logic...")
    # call verification script or just run logic here?
    # Running verify_loan_list.py is easier
    exit_code = os.system('python verify_loan_list.py')
    print(f"verify_loan_list.py exit code: {exit_code}")

if __name__ == "__main__":
    fix_and_verify()
