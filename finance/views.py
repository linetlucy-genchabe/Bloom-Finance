import json
import time
import random
from datetime import date, timedelta
from calendar import monthrange

from django.conf import settings
from django.contrib import messages
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    BILLING_CYCLES, EXPENSE_CATEGORIES, INCOME_TYPES, INVESTMENT_TYPES,
    PAYMENT_METHODS, SUBSCRIPTION_CATEGORIES,
    Expense, Goal, Income, Investment, SavingsAccount, SavingsBalanceHistory,
    Subscription, UserProfile,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_profile():
    profile = UserProfile.objects.first()
    if not profile:
        profile = UserProfile.objects.create()
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
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
    request.session.modified = True
    return redirect('pin_login')


def profile_settings(request):
    profile = get_profile()
    if request.method == 'POST':
        profile.display_name = request.POST.get('display_name', profile.display_name).strip()
        profile.currency     = request.POST.get('currency', profile.currency)
        profile.avatar_emoji = request.POST.get('avatar', profile.avatar_emoji)
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
    month_income     = Income.objects.filter(date__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
    total_savings    = SavingsAccount.objects.filter(is_active=True).aggregate(Sum('balance'))['balance__sum'] or 0
    total_invest_val = Investment.objects.filter(is_active=True).aggregate(Sum('current_value'))['current_value__sum'] or 0
    total_invested   = Investment.objects.filter(is_active=True).aggregate(Sum('amount_invested'))['amount_invested__sum'] or 0

    subs         = list(Subscription.objects.filter(is_active=True))
    monthly_subs = round(sum(s.monthly_cost for s in subs), 2)
    net_worth    = float(total_savings) + float(total_invest_val)
    net_balance  = float(month_income) - float(month_expenses)

    recent_expenses = list(Expense.objects.all()[:5])
    active_goals    = list(Goal.objects.filter(status='active').order_by('priority')[:4])
    upcoming_subs   = [s for s in subs if 0 <= s.days_until_renewal <= 7]

    cat_data = []
    for key, label in EXPENSE_CATEGORIES:
        amt = Expense.objects.filter(category=key, date__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
        if amt:
            cat_data.append({'category': label.split(' ', 1)[-1], 'amount': float(amt)})

    monday = today - timedelta(days=today.weekday())
    weekly_data = []
    for i in range(7):
        d   = monday + timedelta(days=i)
        amt = Expense.objects.filter(date=d).aggregate(Sum('amount'))['amount__sum'] or 0
        weekly_data.append({'day': d.strftime('%a'), 'amount': float(amt), 'is_today': d == today})

    quotes = [
        ("She believed she could, so she did.", "R.S. Grey"),
        ("A budget is telling your money where to go.", "Dave Ramsey"),
        ("Do not save what is left after spending; spend what is left after saving.", "Warren Buffett"),
        ("Financial freedom is available to those who learn about it.", "Robert Kiyosaki"),
        ("The secret to getting ahead is getting started.", "Mark Twain"),
        ("Wealth is not about having a lot of money; it's about having a lot of options.", "Chris Rock"),
    ]
    quote, quote_author = random.choice(quotes)

    return render(request, 'dashboard.html', {
        'profile': profile, 'today': today,
        'month_expenses': month_expenses, 'month_income': month_income,
        'net_balance': net_balance, 'total_savings': total_savings,
        'total_invest_val': total_invest_val, 'total_invested': total_invested,
        'monthly_subs': monthly_subs, 'net_worth': net_worth,
        'subs_count': len(subs),
        'recent_expenses': recent_expenses, 'active_goals': active_goals,
        'upcoming_subs': upcoming_subs,
        'cat_data': json.dumps(cat_data),
        'weekly_data': json.dumps(weekly_data),
        'quote': quote, 'quote_author': quote_author,
    })


# ─────────────────────────────────────────────────────────────────────────────
# INCOME
# ─────────────────────────────────────────────────────────────────────────────

def income_list(request):
    qs     = Income.objects.all()
    month  = request.GET.get('month', '')
    search = request.GET.get('search', '')
    if month:
        y, m = month.split('-')
        qs = qs.filter(date__year=y, date__month=m)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(notes__icontains=search))
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0

    type_data = []
    for key, label in INCOME_TYPES:
        amt = Income.objects.filter(income_type=key).aggregate(Sum('amount'))['amount__sum'] or 0
        if amt:
            type_data.append({'type': label.split(' ', 1)[-1], 'amount': float(amt)})

    # 6-month income vs expenses vs savings
    today = date.today()
    monthly_comparison = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0: m += 12; y -= 1
        inc  = Income.objects.filter(date__year=y, date__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
        exp  = Expense.objects.filter(date__year=y, date__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
        # savings = deposits logged in balance history that month
        sav  = SavingsBalanceHistory.objects.filter(date__year=y, date__month=m).aggregate(Sum('balance'))['balance__sum'] or 0
        monthly_comparison.append({
            'month': date(y, m, 1).strftime('%b'),
            'income': float(inc),
            'expenses': float(exp),
            'savings': float(sav),
        })

    return render(request, 'income.html', {
        'income_list': qs, 'total': total,
        'income_types': INCOME_TYPES,
        'selected_month': month, 'search': search,
        'type_data': json.dumps(type_data),
        'monthly_comparison': json.dumps(monthly_comparison),
    })


def income_add(request):
    if request.method == 'POST':
        Income.objects.create(
            title=request.POST['title'], amount=request.POST['amount'],
            income_type=request.POST['income_type'], date=request.POST['date'],
            notes=request.POST.get('notes', ''),
            is_recurring=request.POST.get('is_recurring') == 'on',
        )
        messages.success(request, 'Income recorded! 💚')
        return redirect('income')
    return render(request, 'income_form.html', {
        'income_types': INCOME_TYPES, 'today': date.today().isoformat(),
    })


def income_edit(request, pk):
    inc = get_object_or_404(Income, pk=pk)
    if request.method == 'POST':
        inc.title        = request.POST['title']
        inc.amount       = request.POST['amount']
        inc.income_type  = request.POST['income_type']
        inc.date         = request.POST['date']
        inc.notes        = request.POST.get('notes', '')
        inc.is_recurring = request.POST.get('is_recurring') == 'on'
        inc.save()
        messages.success(request, 'Income updated! ✨')
        return redirect('income')
    return render(request, 'income_form.html', {
        'income': inc, 'income_types': INCOME_TYPES, 'today': date.today().isoformat(),
    })


def income_delete(request, pk):
    inc = get_object_or_404(Income, pk=pk)
    if request.method == 'POST':
        inc.delete()
        messages.success(request, 'Income entry deleted.')
    return redirect('income')


# ─────────────────────────────────────────────────────────────────────────────
# SAVINGS  (simplified — track existing bank accounts)
# ─────────────────────────────────────────────────────────────────────────────

def savings_list(request):
    accounts      = SavingsAccount.objects.filter(is_active=True)
    total_savings = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    return render(request, 'savings.html', {
        'accounts': accounts, 'total_savings': total_savings,
        'goals': Goal.objects.filter(status='active'),
    })


def savings_add(request):
    if request.method == 'POST':
        goal_id = request.POST.get('linked_goal', '')
        acc = SavingsAccount(
            name=request.POST['name'],
            bank_name=request.POST.get('bank_name', ''),
            emoji=request.POST.get('emoji', '🏦'),
            description=request.POST.get('description', ''),
            balance=request.POST.get('balance', 0),
        )
        if goal_id:
            acc.linked_goal = Goal.objects.filter(pk=goal_id).first()
        acc.save()
        # Record initial balance in history
        if float(request.POST.get('balance', 0)) > 0:
            SavingsBalanceHistory.objects.create(
                account=acc, balance=acc.balance,
                notes='Opening balance', date=date.today(),
            )
        messages.success(request, f'Account "{acc.name}" added! 🏦')
        return redirect('savings')
    return render(request, 'savings_form.html', {
        'goals': Goal.objects.filter(status='active'),
    })


def savings_edit(request, pk):
    acc = get_object_or_404(SavingsAccount, pk=pk)
    if request.method == 'POST':
        acc.name      = request.POST['name']
        acc.bank_name = request.POST.get('bank_name', '')
        acc.emoji     = request.POST.get('emoji', acc.emoji)
        acc.description = request.POST.get('description', '')
        goal_id = request.POST.get('linked_goal', '')
        acc.linked_goal = Goal.objects.filter(pk=goal_id).first() if goal_id else None
        acc.save()
        messages.success(request, 'Account updated! ✨')
        return redirect('savings')
    return render(request, 'savings_form.html', {
        'account': acc, 'goals': Goal.objects.filter(status='active'),
    })


def savings_detail(request, pk):
    acc     = get_object_or_404(SavingsAccount, pk=pk)
    history = acc.history.all()[:24]

    # Build chart data from history
    chart_data = [{'date': str(h.date), 'balance': float(h.balance)} for h in reversed(list(history))]

    return render(request, 'savings_detail.html', {
        'account': acc, 'history': history,
        'chart_data': json.dumps(chart_data),
    })


def savings_update_balance(request, pk):
    """Update the current balance — records a snapshot in history."""
    acc = get_object_or_404(SavingsAccount, pk=pk)
    if request.method == 'POST':
        new_balance = request.POST.get('balance', '')
        notes       = request.POST.get('notes', '')
        try:
            new_balance = float(new_balance)
        except ValueError:
            messages.error(request, 'Invalid balance amount.')
            return redirect('savings_detail', pk=pk)

        acc.balance = new_balance
        acc.save()

        SavingsBalanceHistory.objects.create(
            account=acc, balance=new_balance,
            notes=notes, date=request.POST.get('date') or date.today(),
        )

        # Update linked goal saved_amount if any
        if acc.linked_goal:
            acc.linked_goal.saved_amount = new_balance
            if float(new_balance) >= float(acc.linked_goal.target_amount):
                acc.linked_goal.status = 'achieved'
                messages.success(request, f'🎉 Goal "{acc.linked_goal.name}" achieved!')
            acc.linked_goal.save()

        messages.success(request, f'Balance updated to {acc.balance:,.2f}! 💚')
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
    investments    = Investment.objects.filter(is_active=True)
    total_invested = investments.aggregate(Sum('amount_invested'))['amount_invested__sum'] or 0
    total_value    = investments.aggregate(Sum('current_value'))['current_value__sum'] or 0
    total_gain     = float(total_value) - float(total_invested)
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
    subs          = list(Subscription.objects.filter(is_active=True))
    total_monthly = sum(s.monthly_cost for s in subs)
    upcoming      = [s for s in subs if 0 <= s.days_until_renewal <= 7]

    # Suggest recurring expenses not already in subscriptions
    existing_names = [s.name.lower() for s in subs]
    suggestions = list(
        Expense.objects.filter(is_recurring=True)
        .exclude(title__iregex='|'.join(existing_names) if existing_names else 'NOMATCH_XYZ')
        .values('title', 'amount', 'category')
        .distinct()[:10]
    )

    return render(request, 'subscriptions.html', {
        'subscriptions': subs,
        'total_monthly': round(total_monthly, 2),
        'total_yearly': round(total_monthly * 12, 2),
        'upcoming': upcoming,
        'suggestions': suggestions,
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


def subscription_add_from_expense(request):
    """Confirm a suggested recurring expense as a subscription."""
    if request.method == 'POST':
        Subscription.objects.create(
            name=request.POST['name'], category=request.POST.get('category', 'other'),
            emoji='📱', amount=request.POST['amount'],
            billing_cycle='monthly',
            next_billing_date=request.POST.get('next_billing_date', date.today().replace(day=1)),
            notes='Added from recurring expense',
        )
        messages.success(request, f'"{request.POST["name"]}" added to subscriptions! 📱')
    return redirect('subscriptions')


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


# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def monthly_analysis(request):
    today = date.today()
    try:
        year  = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year, month = today.year, today.month
    if month < 1:  month = 1
    if month > 12: month = 12

    month_start = date(year, month, 1)
    month_label = month_start.strftime('%B %Y')
    profile     = get_profile()

    total_income   = Income.objects.filter(date__year=year, date__month=month).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = Expense.objects.filter(date__year=year, date__month=month).aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance    = float(total_income) - float(total_expenses)

    total_saved = SavingsBalanceHistory.objects.filter(
        date__year=year, date__month=month
    ).aggregate(Sum('balance'))['balance__sum'] or 0

    subs         = list(Subscription.objects.filter(is_active=True))
    monthly_subs = round(sum(s.monthly_cost for s in subs), 2)

    goals_achieved = Goal.objects.filter(status='achieved', updated_at__year=year, updated_at__month=month)

    cat_breakdown = []
    for key, label in EXPENSE_CATEGORIES:
        amt = Expense.objects.filter(category=key, date__year=year, date__month=month).aggregate(Sum('amount'))['amount__sum'] or 0
        if amt:
            cat_breakdown.append({
                'key': key, 'label': label, 'amount': float(amt),
                'percent': round(float(amt) / float(total_expenses) * 100, 1) if total_expenses else 0,
            })
    cat_breakdown.sort(key=lambda x: x['amount'], reverse=True)

    income_breakdown = []
    for key, label in INCOME_TYPES:
        amt = Income.objects.filter(income_type=key, date__year=year, date__month=month).aggregate(Sum('amount'))['amount__sum'] or 0
        if amt:
            income_breakdown.append({'label': label, 'amount': float(amt)})

    daily_data = []
    for day in range(1, monthrange(year, month)[1] + 1):
        d   = date(year, month, day)
        amt = Expense.objects.filter(date=d).aggregate(Sum('amount'))['amount__sum'] or 0
        daily_data.append({'day': day, 'amount': float(amt)})

    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year if month < 12 else year + 1

    month_options = []
    for y in range(today.year - 2, today.year + 2):
        for m in range(1, 13):
            month_options.append({
                'year': y, 'month': m,
                'label': date(y, m, 1).strftime('%B %Y'),
                'selected': y == year and m == month,
            })

    return render(request, 'analysis.html', {
        'profile': profile, 'month_label': month_label,
        'year': year, 'month': month,
        'prev_month': prev_month, 'prev_year': prev_year,
        'next_month': next_month, 'next_year': next_year,
        'total_income': total_income, 'total_expenses': total_expenses,
        'net_balance': net_balance, 'total_saved': total_saved,
        'monthly_subs': monthly_subs, 'goals_achieved': goals_achieved,
        'cat_breakdown': cat_breakdown, 'income_breakdown': income_breakdown,
        'daily_data': json.dumps(daily_data),
        'cat_chart_data': json.dumps([{'label': c['label'].split(' ', 1)[-1], 'amount': c['amount']} for c in cat_breakdown]),
        'month_options': month_options,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PWA
# ─────────────────────────────────────────────────────────────────────────────

def offline(request):
    return render(request, 'offline.html')


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
            messages.success(request, 'Expense added! 💸')
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