import json
import time
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    BILLING_CYCLES, EXPENSE_CATEGORIES, GOAL_PRIORITIES, INVESTMENT_TYPES,
    PAYMENT_METHODS, SUBSCRIPTION_CATEGORIES,
    Expense, Goal, Investment, SavingsAccount, SavingsTransaction,
    Subscription, UserProfile,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_profile():
    """Always return the single user profile, creating it only if none exists."""
    profile = UserProfile.objects.first()
    if not profile:
        profile = UserProfile.objects.create()
    return profile

# ─────────────────────────────────────────────────────────────────────────────
# AUTH — PIN login, setup, unlock, lock
# ─────────────────────────────────────────────────────────────────────────────

def pin_login(request):
    profile = get_profile()
    if not profile.pin_hash:
        return redirect('setup')

    expired = request.session.pop('session_expired', False)

    if request.method == 'POST':
        entered_pin = request.POST.get('pin', '').strip()
        if profile.check_pin(entered_pin):
            request.session[settings.PIN_SESSION_KEY] = True
            request.session['pin_auth_time'] = time.time()
            request.session.modified = True
            return redirect('dashboard')
        messages.error(request, 'Incorrect PIN. Try again.')

    return render(request, 'pin_login.html', {'profile': profile, 'expired': expired})


def setup(request):
    profile = get_profile()
    if profile.pin_hash and not request.session.get('setup_mode'):
        return redirect('pin_login')

    if request.method == 'POST':
        pin         = request.POST.get('pin', '').strip()
        pin_confirm = request.POST.get('pin_confirm', '').strip()

        if not pin.isdigit() or len(pin) < 4:
            messages.error(request, 'PIN must be at least 4 digits.')
        elif pin != pin_confirm:
            messages.error(request, 'PINs do not match.')
        else:
            profile.display_name = request.POST.get('display_name', 'Friend').strip() or 'Friend'
            profile.avatar_emoji = request.POST.get('avatar', '🌸')
            profile.currency     = request.POST.get('currency', 'KES')
            profile.set_pin(pin)

            phrase = request.POST.get('passphrase', '').strip()
            if phrase:
                profile.set_passphrase(phrase)

            profile.save()

            # Verify PIN actually saved to DB before creating session
            fresh = UserProfile.objects.get(pk=profile.pk)
            if not fresh.check_pin(pin):
                messages.error(request, 'Something went wrong saving your PIN. Please try again.')
                return render(request, 'setup.html', {'profile': profile})

            request.session[settings.PIN_SESSION_KEY] = True
            request.session['pin_auth_time'] = time.time()
            request.session.modified = True
            request.session.pop('setup_mode', None)
            messages.success(request, f'Welcome to Bloom Finance, {profile.display_name}! 🌸')
            return redirect('dashboard')

    return render(request, 'setup.html', {'profile': profile})

def unlock(request):
    profile = get_profile()
    if request.method == 'POST':
        if profile.check_passphrase(request.POST.get('passphrase', '')):
            request.session['setup_mode'] = True
            return redirect('setup')
        messages.error(request, 'Incorrect passphrase.')
    return render(request, 'unlock.html', {'profile': profile})


def lock(request):
    request.session[settings.PIN_SESSION_KEY] = False
    return redirect('pin_login')


def profile_settings(request):
    profile = get_profile()
    if request.method == 'POST':
        profile.display_name  = request.POST.get('display_name', profile.display_name).strip()
        profile.currency      = request.POST.get('currency', profile.currency)
        profile.avatar_emoji  = request.POST.get('avatar', profile.avatar_emoji)
        try:
            profile.monthly_budget = float(request.POST.get('monthly_budget', 0))
        except ValueError:
            profile.monthly_budget = 0

        new_pin = request.POST.get('new_pin', '').strip()
        if new_pin:
            if len(new_pin) >= 4 and new_pin.isdigit():
                profile.set_pin(new_pin)
            else:
                messages.error(request, 'PIN must be at least 4 digits.')
                return render(request, 'settings.html', {'profile': profile})

        new_phrase = request.POST.get('new_passphrase', '').strip()
        if new_phrase:
            profile.set_passphrase(new_phrase)

        profile.save()
        messages.success(request, 'Settings saved! ✨')
        return redirect('settings')

    return render(request, 'settings.html', {'profile': profile})


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def dashboard(request):
    today       = date.today()
    month_start = today.replace(day=1)
    profile     = get_profile()

    month_expenses   = Expense.objects.filter(date__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
    total_savings    = SavingsAccount.objects.filter(is_active=True).aggregate(Sum('balance'))['balance__sum'] or 0
    total_invest_val = Investment.objects.filter(is_active=True).aggregate(Sum('current_value'))['current_value__sum'] or 0
    total_invested   = Investment.objects.filter(is_active=True).aggregate(Sum('amount_invested'))['amount_invested__sum'] or 0
    subs             = Subscription.objects.filter(is_active=True)
    monthly_subs     = sum(s.monthly_cost for s in subs)
    net_worth        = float(total_savings) + float(total_invest_val)

    recent_expenses = Expense.objects.all()[:5]
    active_goals    = Goal.objects.filter(status='active')[:4]
    upcoming_subs   = [s for s in subs if 0 <= s.days_until_renewal <= 7]

    # Spending by category this month
    cat_data = []
    for key, label in EXPENSE_CATEGORIES:
        amt = Expense.objects.filter(category=key, date__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
        if amt:
            cat_data.append({'category': label.split(' ', 1)[-1], 'amount': float(amt)})

    # Last 7 days
    weekly_data = []
    for i in range(6, -1, -1):
        d   = today - timedelta(days=i)
        amt = Expense.objects.filter(date=d).aggregate(Sum('amount'))['amount__sum'] or 0
        weekly_data.append({'day': d.strftime('%a'), 'amount': float(amt)})

    import random
    quotes = [
        ("She believed she could, so she did.", "R.S. Grey"),
        ("A budget is telling your money where to go.", "Dave Ramsey"),
        ("Do not save what is left after spending; spend what is left after saving.", "Warren Buffett"),
        ("Financial freedom is available to those who learn about it.", "Robert Kiyosaki"),
        ("The secret to getting ahead is getting started.", "Mark Twain"),
    ]
    quote, quote_author = random.choice(quotes)

    return render(request, 'dashboard.html', {
        'profile': profile, 'today': today,
        'month_expenses': month_expenses, 'total_savings': total_savings,
        'total_invest_val': total_invest_val, 'total_invested': total_invested,
        'monthly_subs': monthly_subs, 'net_worth': net_worth,
        'recent_expenses': recent_expenses, 'active_goals': active_goals,
        'upcoming_subs': upcoming_subs,
        'cat_data': json.dumps(cat_data),
        'weekly_data': json.dumps(weekly_data),
        'quote': quote, 'quote_author': quote_author,
    })


# ─────────────────────────────────────────────────────────────────────────────
# EXPENSES
# ─────────────────────────────────────────────────────────────────────────────

def expense_list(request):
    qs       = Expense.objects.all()
    category = request.GET.get('category', '')
    month    = request.GET.get('month', '')
    search   = request.GET.get('search', '')

    if category: qs = qs.filter(category=category)
    if month:
        y, m = month.split('-')
        qs = qs.filter(date__year=y, date__month=m)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(notes__icontains=search))

    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0

    # 6-month bar chart
    today = date.today()
    monthly_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0: m += 12; y -= 1
        amt = Expense.objects.filter(date__year=y, date__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_data.append({'month': date(y, m, 1).strftime('%b'), 'amount': float(amt)})

    return render(request, 'expenses.html', {
        'expenses': qs, 'total': total,
        'categories': EXPENSE_CATEGORIES,
        'selected_category': category, 'selected_month': month, 'search': search,
        'monthly_data': json.dumps(monthly_data),
    })


def expense_add(request):
    if request.method == 'POST':
        try:
            Expense.objects.create(
                title=request.POST['title'], amount=request.POST['amount'],
                category=request.POST['category'], payment_method=request.POST['payment_method'],
                date=request.POST['date'], notes=request.POST.get('notes', ''),
                is_recurring=request.POST.get('is_recurring') == 'on',
                tags=request.POST.get('tags', ''),
            )
            messages.success(request, f'Expense added! 💸')
            return redirect('expenses')
        except Exception as e:
            messages.error(request, f'Error: {e}')
    return render(request, 'expense_form.html', {
        'categories': EXPENSE_CATEGORIES, 'payment_methods': PAYMENT_METHODS,
        'today': date.today().isoformat(),
    })


def expense_edit(request, pk):
    exp = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        exp.title          = request.POST['title']
        exp.amount         = request.POST['amount']
        exp.category       = request.POST['category']
        exp.payment_method = request.POST['payment_method']
        exp.date           = request.POST['date']
        exp.notes          = request.POST.get('notes', '')
        exp.is_recurring   = request.POST.get('is_recurring') == 'on'
        exp.tags           = request.POST.get('tags', '')
        exp.save()
        messages.success(request, 'Expense updated! ✨')
        return redirect('expenses')
    return render(request, 'expense_form.html', {
        'expense': exp, 'categories': EXPENSE_CATEGORIES,
        'payment_methods': PAYMENT_METHODS, 'today': date.today().isoformat(),
    })


def expense_delete(request, pk):
    exp = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        exp.delete()
        messages.success(request, 'Expense deleted.')
    return redirect('expenses')


# ─────────────────────────────────────────────────────────────────────────────
# SAVINGS
# ─────────────────────────────────────────────────────────────────────────────

def savings_list(request):
    accounts      = SavingsAccount.objects.filter(is_active=True)
    total_savings = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    return render(request, 'savings.html', {'accounts': accounts, 'total_savings': total_savings})


def savings_add(request):
    if request.method == 'POST':
        SavingsAccount.objects.create(
            name=request.POST['name'], emoji=request.POST.get('emoji', '💰'),
            description=request.POST.get('description', ''),
            balance=request.POST.get('balance', 0), target=request.POST.get('target', 0),
            interest_rate=request.POST.get('interest_rate', 0),
        )
        messages.success(request, 'Savings account created! 🌱')
        return redirect('savings')
    return render(request, 'savings_form.html', {})


def savings_edit(request, pk):
    acc = get_object_or_404(SavingsAccount, pk=pk)
    if request.method == 'POST':
        acc.name          = request.POST['name']
        acc.emoji         = request.POST.get('emoji', acc.emoji)
        acc.description   = request.POST.get('description', '')
        acc.target        = request.POST.get('target', acc.target)
        acc.interest_rate = request.POST.get('interest_rate', acc.interest_rate)
        acc.save()
        messages.success(request, 'Account updated! ✨')
        return redirect('savings')
    return render(request, 'savings_form.html', {'account': acc})


def savings_detail(request, pk):
    acc          = get_object_or_404(SavingsAccount, pk=pk)
    transactions = acc.transactions.all()[:30]
    return render(request, 'savings_detail.html', {'account': acc, 'transactions': transactions})


def savings_transact(request, pk):
    acc = get_object_or_404(SavingsAccount, pk=pk)
    if request.method == 'POST':
        amount   = float(request.POST['amount'])
        tx_type  = request.POST.get('transaction_type', 'deposit')
        if tx_type == 'withdrawal' and amount > float(acc.balance):
            messages.error(request, 'Insufficient balance.')
        else:
            acc.balance += amount if tx_type != 'withdrawal' else -amount
            acc.save()
            SavingsTransaction.objects.create(
                account=acc, transaction_type=tx_type, amount=amount,
                notes=request.POST.get('notes', ''),
                date=request.POST.get('date') or date.today(),
            )
            messages.success(request, 'Transaction recorded! 💚')
    return redirect('savings_detail', pk=pk)


def savings_delete(request, pk):
    acc = get_object_or_404(SavingsAccount, pk=pk)
    if request.method == 'POST':
        acc.is_active = False
        acc.save()
        messages.success(request, 'Account archived.')
    return redirect('savings')


# ─────────────────────────────────────────────────────────────────────────────
# INVESTMENTS
# ─────────────────────────────────────────────────────────────────────────────

def investment_list(request):
    investments      = Investment.objects.filter(is_active=True)
    total_invested   = investments.aggregate(Sum('amount_invested'))['amount_invested__sum'] or 0
    total_value      = investments.aggregate(Sum('current_value'))['current_value__sum'] or 0
    total_gain       = float(total_value) - float(total_invested)

    type_data = []
    for key, label in INVESTMENT_TYPES:
        val = investments.filter(investment_type=key).aggregate(Sum('current_value'))['current_value__sum'] or 0
        if val:
            type_data.append({'type': label, 'value': float(val)})

    return render(request, 'investments.html', {
        'investments': investments, 'total_invested': total_invested,
        'total_value': total_value, 'total_gain': total_gain,
        'type_data': json.dumps(type_data),
    })


def investment_add(request):
    if request.method == 'POST':
        Investment.objects.create(
            name=request.POST['name'], investment_type=request.POST['investment_type'],
            amount_invested=request.POST['amount_invested'], current_value=request.POST['current_value'],
            notes=request.POST.get('notes', ''), date_invested=request.POST['date_invested'],
        )
        messages.success(request, 'Investment added! 📈')
        return redirect('investments')
    return render(request, 'investment_form.html', {'investment_types': INVESTMENT_TYPES})


def investment_edit(request, pk):
    inv = get_object_or_404(Investment, pk=pk)
    if request.method == 'POST':
        inv.name            = request.POST['name']
        inv.investment_type = request.POST['investment_type']
        inv.amount_invested = request.POST['amount_invested']
        inv.current_value   = request.POST['current_value']
        inv.notes           = request.POST.get('notes', '')
        inv.date_invested   = request.POST['date_invested']
        inv.save()
        messages.success(request, 'Investment updated! ✨')
        return redirect('investments')
    return render(request, 'investment_form.html', {'inv': inv, 'investment_types': INVESTMENT_TYPES})


def investment_delete(request, pk):
    inv = get_object_or_404(Investment, pk=pk)
    if request.method == 'POST':
        inv.is_active = False
        inv.save()
        messages.success(request, 'Investment archived.')
    return redirect('investments')


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTIONS
# ─────────────────────────────────────────────────────────────────────────────

def subscription_list(request):
    subs          = Subscription.objects.filter(is_active=True)
    total_monthly = sum(s.monthly_cost for s in subs)
    upcoming      = [s for s in subs if 0 <= s.days_until_renewal <= 7]
    return render(request, 'subscriptions.html', {
        'subscriptions': subs, 'total_monthly': round(total_monthly, 2),
        'total_yearly': round(total_monthly * 12, 2), 'upcoming': upcoming,
    })


def subscription_add(request):
    if request.method == 'POST':
        Subscription.objects.create(
            name=request.POST['name'], category=request.POST['category'],
            emoji=request.POST.get('emoji', '📱'), amount=request.POST['amount'],
            billing_cycle=request.POST['billing_cycle'],
            next_billing_date=request.POST['next_billing_date'],
            website=request.POST.get('website', ''), notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Subscription added! 📱')
        return redirect('subscriptions')
    return render(request, 'subscription_form.html', {
        'categories': SUBSCRIPTION_CATEGORIES, 'billing_cycles': BILLING_CYCLES,
        'today': date.today().isoformat(),
    })


def subscription_edit(request, pk):
    sub = get_object_or_404(Subscription, pk=pk)
    if request.method == 'POST':
        sub.name              = request.POST['name']
        sub.category          = request.POST['category']
        sub.emoji             = request.POST.get('emoji', sub.emoji)
        sub.amount            = request.POST['amount']
        sub.billing_cycle     = request.POST['billing_cycle']
        sub.next_billing_date = request.POST['next_billing_date']
        sub.website           = request.POST.get('website', '')
        sub.notes             = request.POST.get('notes', '')
        sub.save()
        messages.success(request, 'Subscription updated! ✨')
        return redirect('subscriptions')
    return render(request, 'subscription_form.html', {
        'sub': sub, 'categories': SUBSCRIPTION_CATEGORIES,
        'billing_cycles': BILLING_CYCLES, 'today': date.today().isoformat(),
    })


def subscription_delete(request, pk):
    sub = get_object_or_404(Subscription, pk=pk)
    if request.method == 'POST':
        sub.is_active = False
        sub.save()
        messages.success(request, f'"{sub.name}" cancelled.')
    return redirect('subscriptions')


# ─────────────────────────────────────────────────────────────────────────────
# GOALS
# ─────────────────────────────────────────────────────────────────────────────

def goal_list(request):
    return render(request, 'goals.html', {
        'active_goals':   Goal.objects.filter(status='active'),
        'achieved_goals': Goal.objects.filter(status='achieved'),
    })


def goal_add(request):
    if request.method == 'POST':
        goal = Goal(
            name=request.POST['name'], emoji=request.POST.get('emoji', '🎯'),
            description=request.POST.get('description', ''),
            target_amount=request.POST['target_amount'],
            saved_amount=request.POST.get('saved_amount', 0),
            priority=request.POST.get('priority', 'medium'),
        )
        td = request.POST.get('target_date', '')
        if td: goal.target_date = td
        goal.save()
        messages.success(request, f'Goal "{goal.name}" created! 🎯')
        return redirect('goals')
    return render(request, 'goal_form.html', {'today': date.today().isoformat()})


def goal_edit(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == 'POST':
        goal.name          = request.POST['name']
        goal.emoji         = request.POST.get('emoji', goal.emoji)
        goal.description   = request.POST.get('description', '')
        goal.target_amount = request.POST['target_amount']
        goal.saved_amount  = request.POST.get('saved_amount', goal.saved_amount)
        goal.priority      = request.POST.get('priority', goal.priority)
        goal.status        = request.POST.get('status', goal.status)
        td = request.POST.get('target_date', '')
        goal.target_date   = td if td else None
        goal.save()
        if goal.status == 'achieved':
            messages.success(request, f'🎉 You achieved "{goal.name}"!')
        else:
            messages.success(request, 'Goal updated! 💪')
        return redirect('goals')
    return render(request, 'goal_form.html', {'goal': goal, 'today': date.today().isoformat()})


def goal_contribute(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        goal.saved_amount = float(goal.saved_amount) + amount
        if goal.saved_amount >= float(goal.target_amount):
            goal.status = 'achieved'
            messages.success(request, f'🎉 Amazing! You achieved: {goal.name}!')
        else:
            messages.success(request, f'Added to "{goal.name}"! 💚')
        goal.save()
    return redirect('goals')


def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Goal removed.')
    return redirect('goals')

# ── PWA ───────────────────────────────────────────────────────────────────────

def offline(request):
    return render(request, 'offline.html')