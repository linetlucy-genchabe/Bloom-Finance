import hashlib
from django.db import models
from django.utils import timezone
from datetime import date


# ── USER PROFILE ──────────────────────────────────────────────────────────────

class UserProfile(models.Model):
    display_name    = models.CharField(max_length=100, default='Friend')
    pin_hash        = models.CharField(max_length=64, blank=True)
    passphrase_hash = models.CharField(max_length=64, blank=True)
    avatar_emoji    = models.CharField(max_length=10, default='🌸')
    currency        = models.CharField(max_length=10, default='KES')
    monthly_budget  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    def set_pin(self, pin):
        self.pin_hash = hashlib.sha256(pin.encode()).hexdigest()

    def check_pin(self, pin):
        return self.pin_hash == hashlib.sha256(pin.encode()).hexdigest()

    def set_passphrase(self, phrase):
        self.passphrase_hash = hashlib.sha256(phrase.lower().strip().encode()).hexdigest()

    def check_passphrase(self, phrase):
        return self.passphrase_hash == hashlib.sha256(phrase.lower().strip().encode()).hexdigest()


# ── EXPENSES ──────────────────────────────────────────────────────────────────

EXPENSE_CATEGORIES = [
    ('food','🍽️ Food & Dining'), ('transport','🚗 Transport'), ('utilities','💡 Utilities'),
    ('health','💊 Health & Medical'), ('shopping','🛍️ Shopping'), ('entertainment','🎬 Entertainment'),
    ('education','📚 Education'), ('rent','🏠 Rent & Housing'), ('personal','💄 Personal Care'),
    ('family','👨‍👩‍👧 Family'), ('business','💼 Business'), ('travel','✈️ Travel'), ('other','📦 Other'),
]
PAYMENT_METHODS = [('mpesa','M-Pesa'), ('cash','Cash'), ('card','Bank Card'), ('bank','Bank Transfer'), ('other','Other')]


class Expense(models.Model):
    title          = models.CharField(max_length=200)
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    category       = models.CharField(max_length=50, choices=EXPENSE_CATEGORIES, default='other')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='mpesa')
    date           = models.DateField(default=timezone.now)
    notes          = models.TextField(blank=True)
    is_recurring   = models.BooleanField(default=False)
    tags           = models.CharField(max_length=200, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.title} — {self.amount}'

    @property
    def category_label(self):
        return dict(EXPENSE_CATEGORIES).get(self.category, self.category)

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


# ── SAVINGS ───────────────────────────────────────────────────────────────────

class SavingsAccount(models.Model):
    name          = models.CharField(max_length=200)
    emoji         = models.CharField(max_length=10, default='💰')
    description   = models.TextField(blank=True)
    balance       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def progress_percent(self):
        if self.target > 0:
            return min(100, round(float(self.balance) / float(self.target) * 100, 1))
        return 0


SAVINGS_TX_TYPES = [('deposit','Deposit'), ('withdrawal','Withdrawal'), ('interest','Interest')]


class SavingsTransaction(models.Model):
    account          = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=SAVINGS_TX_TYPES, default='deposit')
    amount           = models.DecimalField(max_digits=12, decimal_places=2)
    notes            = models.CharField(max_length=300, blank=True)
    date             = models.DateField(default=timezone.now)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.account.name} — {self.transaction_type} — {self.amount}'


# ── INVESTMENTS ───────────────────────────────────────────────────────────────

INVESTMENT_TYPES = [
    ('stocks','📈 Stocks'), ('crypto','🪙 Crypto'), ('sacco','🏦 SACCO'),
    ('bonds','📜 Gov. Bonds'), ('money_market','💹 Money Market'),
    ('real_estate','🏘️ Real Estate'), ('unit_trust','📊 Unit Trust'), ('other','🔮 Other'),
]


class Investment(models.Model):
    name            = models.CharField(max_length=200)
    investment_type = models.CharField(max_length=30, choices=INVESTMENT_TYPES, default='other')
    amount_invested = models.DecimalField(max_digits=12, decimal_places=2)
    current_value   = models.DecimalField(max_digits=12, decimal_places=2)
    notes           = models.TextField(blank=True)
    date_invested   = models.DateField(default=timezone.now)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_invested']

    def __str__(self):
        return self.name

    @property
    def gain_loss(self):
        return float(self.current_value) - float(self.amount_invested)

    @property
    def gain_loss_percent(self):
        if self.amount_invested > 0:
            return round(self.gain_loss / float(self.amount_invested) * 100, 2)
        return 0


# ── SUBSCRIPTIONS ─────────────────────────────────────────────────────────────

BILLING_CYCLES = [('weekly','Weekly'), ('monthly','Monthly'), ('quarterly','Quarterly'), ('yearly','Yearly')]
SUBSCRIPTION_CATEGORIES = [
    ('streaming','📺 Streaming'), ('music','🎵 Music'), ('productivity','⚡ Productivity'),
    ('gaming','🎮 Gaming'), ('fitness','💪 Fitness'), ('news','📰 News & Media'),
    ('cloud','☁️ Cloud Storage'), ('finance','💳 Finance'), ('other','📦 Other'),
]


class Subscription(models.Model):
    name              = models.CharField(max_length=200)
    category          = models.CharField(max_length=30, choices=SUBSCRIPTION_CATEGORIES, default='other')
    emoji             = models.CharField(max_length=10, default='📱')
    amount            = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle     = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    next_billing_date = models.DateField()
    website           = models.URLField(blank=True)
    notes             = models.CharField(max_length=300, blank=True)
    is_active         = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_billing_date']

    def __str__(self):
        return self.name

    @property
    def monthly_cost(self):
        factors = {'weekly': 4.33, 'monthly': 1, 'quarterly': 0.333, 'yearly': 0.0833}
        return round(float(self.amount) * factors.get(self.billing_cycle, 1), 2)

    @property
    def days_until_renewal(self):
        return (self.next_billing_date - date.today()).days

    @property
    def renewal_status(self):
        d = self.days_until_renewal
        if d < 0:  return 'overdue'
        if d <= 3: return 'urgent'
        if d <= 7: return 'soon'
        return 'ok'


# ── GOALS ─────────────────────────────────────────────────────────────────────

GOAL_PRIORITIES = [('high','High'), ('medium','Medium'), ('low','Low')]
GOAL_STATUSES   = [('active','Active'), ('achieved','Achieved 🎉'), ('paused','Paused')]


class Goal(models.Model):
    name          = models.CharField(max_length=200)
    emoji         = models.CharField(max_length=10, default='🎯')
    description   = models.TextField(blank=True)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    saved_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_date   = models.DateField(null=True, blank=True)
    priority      = models.CharField(max_length=10, choices=GOAL_PRIORITIES, default='medium')
    status        = models.CharField(max_length=20, choices=GOAL_STATUSES, default='active')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'target_date']

    def __str__(self):
        return self.name

    @property
    def progress_percent(self):
        if self.target_amount > 0:
            return min(100, round(float(self.saved_amount) / float(self.target_amount) * 100, 1))
        return 0

    @property
    def remaining(self):
        return max(0, float(self.target_amount) - float(self.saved_amount))

    @property
    def days_remaining(self):
        if self.target_date:
            return (self.target_date - date.today()).days
        return None

    @property
    def monthly_needed(self):
        if self.days_remaining and self.days_remaining > 0 and self.remaining > 0:
            return round(self.remaining / (self.days_remaining / 30), 2)
        return None


# ── INCOME ────────────────────────────────────────────────────────────────────

INCOME_TYPES = [
    ('salary',         '💼 Salary'),
    ('freelance',      '💻 Freelance / Side Work'),
    ('field_expense',  '🧾 Field Expense (Reimbursable)'),
    ('business',       '🏢 Business Income'),
    ('investment',     '📈 Investment Returns'),
    ('other',          '📦 Other'),
]


class Income(models.Model):
    title        = models.CharField(max_length=200)
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    income_type  = models.CharField(max_length=30, choices=INCOME_TYPES, default='salary')
    date         = models.DateField(default=timezone.now)
    notes        = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False, help_text='Monthly recurring income')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.title} — {self.amount}'

    @property
    def income_type_label(self):
        return dict(INCOME_TYPES).get(self.income_type, self.income_type)