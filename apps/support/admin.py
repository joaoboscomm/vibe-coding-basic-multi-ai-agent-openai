"""
Admin configuration for support models.
"""
from django.contrib import admin

from .models import Customer, Subscription, Invoice, SupportTicket


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'full_name', 'company_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'company_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'plan', 'status', 'billing_cycle', 'price', 'start_date']
    list_filter = ['plan', 'status', 'billing_cycle', 'created_at']
    search_fields = ['customer__email', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'status', 'total', 'due_date', 'paid_date']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['invoice_number', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'subject', 'category', 'priority', 'status', 'created_at']
    list_filter = ['category', 'priority', 'status', 'created_at']
    search_fields = ['subject', 'description', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']

