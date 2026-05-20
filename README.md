# 🌸 Bloom Finance

Personal finance tracker — expenses, savings, investments, subscriptions, goals. Protected by PIN. Built with Django + PostgreSQL.

---

## 📁 Project Structure

```
bloom_finance_v2/
├── bloom_finance/       # Django project config
│   ├── settings.py      # All settings (postgres, security, static)
│   ├── urls.py          # Root URL — delegates everything to finance/
│   └── wsgi.py
├── finance/             # Single app — all logic here
│   ├── models.py        # ALL models (UserProfile, Expense, Savings, etc.)
│   ├── views.py         # ALL views
│   ├── urls.py          # ALL URL patterns
│   ├── admin.py         # Admin registrations
│   ├── middleware.py    # PIN session auth
│   └── context_processors.py
├── templates/           # All HTML templates (flat — no subfolders)
│   ├── base.html
│   ├── dashboard.html
│   ├── pin_login.html / setup.html / unlock.html / settings.html
│   ├── expenses.html / expense_form.html
│   ├── savings.html / savings_detail.html / savings_form.html
│   ├── investments.html / investment_form.html
│   ├── subscriptions.html / subscription_form.html
│   └── goals.html / goal_form.html
├── static/
│   ├── css/bloom.css    # Full design system (lilac + pink)
│   └── js/bloom.js      # Sidebar, PIN keypad, charts
├── requirements.txt
├── Procfile
├── railway.json
├── runtime.txt
└── .env.example
```

---

## 🚀 Local Setup

### 1. Create the database
```bash
psql -U postgres -c "CREATE DATABASE bloom_finance;"
```

### 2. Install & configure
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DATABASE_URL and a strong SECRET_KEY
```

### 3. Run
```bash
python manage.py migrate
python manage.py runserver
# Visit http://127.0.0.1:8000 → PIN setup on first visit
```

---

## 🚀 Deploy to Railway

1. Push to GitHub
2. Railway → **New Project → Deploy from GitHub**
3. Add **PostgreSQL** plugin (Railway auto-sets `DATABASE_URL`)
4. Set variables: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=.railway.app`
5. Deploy — Railway runs migrate + collectstatic automatically via `Procfile`

---

## 🔐 Auth

- PIN (4–6 digits) set on first visit. No username/password.
- Session auto-locks after **5 minutes** of inactivity.
- Backup passphrase to reset PIN if forgotten.
