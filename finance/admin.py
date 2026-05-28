from django.contrib import admin
from .models import (Income,
    UserProfile, Expense, SavingsAccount, SavingsTransaction,
    Investment, Subscription, Goal,
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'currency', 'created_at']
    exclude = ['pin_hash', 'passphrase_hash']

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'income_type', 'date', 'is_recurring']
    list_filter  = ['income_type', 'date']
    search_fields = ['title', 'notes']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'category', 'date', 'payment_method']
    list_filter  = ['category', 'date']
    search_fields = ['title', 'notes']

@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'balance', 'target', 'is_active']

@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'transaction_type', 'amount', 'date']

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'investment_type', 'amount_invested', 'current_value', 'is_active']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'billing_cycle', 'next_billing_date', 'is_active']

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_amount', 'saved_amount', 'status', 'priority']