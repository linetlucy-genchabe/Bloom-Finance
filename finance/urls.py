from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('',              views.pin_login,       name='pin_login'),
    path('setup/',        views.setup,            name='setup'),
    path('unlock/',       views.unlock,           name='unlock'),
    path('lock/',         views.lock,             name='lock'),
    path('settings/',     views.profile_settings, name='settings'),
    # Dashboard
    path('dashboard/',    views.dashboard,        name='dashboard'),
    # Expenses
    path('expenses/',                     views.expense_list,   name='expenses'),
    path('expenses/add/',                 views.expense_add,    name='expense_add'),
    path('expenses/<int:pk>/edit/',       views.expense_edit,   name='expense_edit'),
    path('expenses/<int:pk>/delete/',     views.expense_delete, name='expense_delete'),
    # Savings
    path('savings/',                      views.savings_list,   name='savings'),
    path('savings/add/',                  views.savings_add,    name='savings_add'),
    path('savings/<int:pk>/',             views.savings_detail, name='savings_detail'),
    path('savings/<int:pk>/edit/',        views.savings_edit,   name='savings_edit'),
    path('savings/<int:pk>/transact/',    views.savings_transact, name='savings_transact'),
    path('savings/<int:pk>/delete/',      views.savings_delete, name='savings_delete'),
    # Investments
    path('investments/',                  views.investment_list,   name='investments'),
    path('investments/add/',              views.investment_add,    name='investment_add'),
    path('investments/<int:pk>/edit/',    views.investment_edit,   name='investment_edit'),
    path('investments/<int:pk>/delete/',  views.investment_delete, name='investment_delete'),
    # Subscriptions
    path('subscriptions/',                views.subscription_list,   name='subscriptions'),
    path('subscriptions/add/',            views.subscription_add,    name='subscription_add'),
    path('subscriptions/<int:pk>/edit/',  views.subscription_edit,   name='subscription_edit'),
    path('subscriptions/<int:pk>/delete/',views.subscription_delete, name='subscription_delete'),
    # Goals
    path('goals/',                        views.goal_list,       name='goals'),
    path('goals/add/',                    views.goal_add,        name='goal_add'),
    path('goals/<int:pk>/edit/',          views.goal_edit,       name='goal_edit'),
    path('goals/<int:pk>/contribute/',    views.goal_contribute, name='goal_contribute'),
    path('goals/<int:pk>/delete/',        views.goal_delete,     name='goal_delete'),
]
