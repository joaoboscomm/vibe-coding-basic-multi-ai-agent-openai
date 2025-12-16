"""
Support domain models for SaaS customer support system.
"""
import uuid
from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel


class Customer(BaseModel):
    """Customer profile for SaaS platform."""
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'customers'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Subscription(BaseModel):
    """SaaS subscription details."""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('trial', 'Trial'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('paused', 'Paused'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    trial_end_date = models.DateField(null=True, blank=True)
    seats = models.IntegerField(default=1)
    features = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.email} - {self.plan} ({self.status})"


class Invoice(BaseModel):
    """Billing history and invoices."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    line_items = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.email} - ${self.total}"


class SupportTicket(BaseModel):
    """Support tickets for escalation handling."""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_customer', 'Waiting on Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('billing', 'Billing'),
        ('technical', 'Technical'),
        ('account', 'Account'),
        ('feature_request', 'Feature Request'),
        ('bug_report', 'Bug Report'),
        ('other', 'Other'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    conversation_id = models.UUIDField(null=True, blank=True, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    assigned_to = models.CharField(max_length=255, blank=True, default='')
    resolution = models.TextField(blank=True, default='')
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.priority.upper()}] {self.subject} - {self.status}"

