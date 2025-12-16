"""
Database lookup tools for customer, subscription, and invoice information.
"""
import logging
import time
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from apps.core.middleware import AgentTracingMiddleware
from apps.support.models import Customer, Subscription, Invoice

logger = logging.getLogger(__name__)


def _format_customer(customer: Customer) -> dict:
    """Format customer data for display."""
    return {
        'id': str(customer.id),
        'email': customer.email,
        'name': customer.full_name,
        'company': customer.company_name or 'N/A',
        'phone': customer.phone or 'N/A',
        'is_active': customer.is_active,
        'member_since': customer.created_at.strftime('%Y-%m-%d'),
    }


def _format_subscription(subscription: Subscription) -> dict:
    """Format subscription data for display."""
    return {
        'id': str(subscription.id),
        'plan': subscription.plan.title(),
        'status': subscription.status.replace('_', ' ').title(),
        'billing_cycle': subscription.billing_cycle.title(),
        'price': f"${subscription.price:.2f}",
        'seats': subscription.seats,
        'start_date': subscription.start_date.strftime('%Y-%m-%d'),
        'end_date': subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else 'N/A',
        'trial_end': subscription.trial_end_date.strftime('%Y-%m-%d') if subscription.trial_end_date else 'N/A',
        'features': subscription.features,
    }


def _format_invoice(invoice: Invoice) -> dict:
    """Format invoice data for display."""
    return {
        'invoice_number': invoice.invoice_number,
        'status': invoice.status.title(),
        'amount': f"${invoice.amount:.2f}",
        'tax': f"${invoice.tax:.2f}",
        'total': f"${invoice.total:.2f}",
        'currency': invoice.currency,
        'due_date': invoice.due_date.strftime('%Y-%m-%d'),
        'paid_date': invoice.paid_date.strftime('%Y-%m-%d') if invoice.paid_date else 'N/A',
        'description': invoice.description or 'N/A',
    }


@tool
def get_customer_info(customer_email: str) -> str:
    """
    Look up customer information by email address.
    Use this to verify customer identity and get basic account information.
    
    Args:
        customer_email: The customer's email address
        
    Returns:
        Customer information including name, company, and account status
    """
    start_time = time.time()
    
    try:
        customer = Customer.objects.get(email=customer_email.lower().strip())
        data = _format_customer(customer)
        
        result = (
            f"**Customer Information**\n"
            f"- Name: {data['name']}\n"
            f"- Email: {data['email']}\n"
            f"- Company: {data['company']}\n"
            f"- Phone: {data['phone']}\n"
            f"- Account Status: {'Active' if data['is_active'] else 'Inactive'}\n"
            f"- Member Since: {data['member_since']}"
        )
        
        logger.info(f"Customer lookup successful for {customer_email}")
        return result
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found: {customer_email}")
        return f"No customer found with email: {customer_email}"
        
    except Exception as e:
        logger.error(f"Customer lookup failed: {e}")
        return f"Error looking up customer: {str(e)}"


@tool
def get_subscription_details(customer_email: str) -> str:
    """
    Get subscription details for a customer.
    Use this to check plan information, billing cycle, and subscription status.
    
    Args:
        customer_email: The customer's email address
        
    Returns:
        Subscription details including plan, status, and billing information
    """
    try:
        customer = Customer.objects.get(email=customer_email.lower().strip())
        subscriptions = Subscription.objects.filter(customer=customer).order_by('-created_at')
        
        if not subscriptions.exists():
            return f"No subscriptions found for {customer_email}"
        
        results = [f"**Subscriptions for {customer.full_name}**\n"]
        
        for sub in subscriptions[:3]:  # Limit to 3 most recent
            data = _format_subscription(sub)
            results.append(
                f"\n**{data['plan']} Plan**\n"
                f"- Status: {data['status']}\n"
                f"- Billing: {data['billing_cycle']} at {data['price']}\n"
                f"- Seats: {data['seats']}\n"
                f"- Start Date: {data['start_date']}\n"
                f"- End Date: {data['end_date']}\n"
                f"- Trial Ends: {data['trial_end']}"
            )
            
            if data['features']:
                features_str = ', '.join(data['features'][:5])
                results.append(f"- Features: {features_str}")
        
        logger.info(f"Subscription lookup successful for {customer_email}")
        return '\n'.join(results)
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found for subscription lookup: {customer_email}")
        return f"No customer found with email: {customer_email}"
        
    except Exception as e:
        logger.error(f"Subscription lookup failed: {e}")
        return f"Error looking up subscription: {str(e)}"


@tool
def get_invoices(customer_email: str, limit: int = 5) -> str:
    """
    Get invoice history for a customer.
    Use this to check billing history, payment status, and outstanding balances.
    
    Args:
        customer_email: The customer's email address
        limit: Maximum number of invoices to return (default: 5)
        
    Returns:
        List of recent invoices with status and amounts
    """
    try:
        customer = Customer.objects.get(email=customer_email.lower().strip())
        invoices = Invoice.objects.filter(customer=customer).order_by('-created_at')[:limit]
        
        if not invoices.exists():
            return f"No invoices found for {customer_email}"
        
        results = [f"**Invoice History for {customer.full_name}**\n"]
        
        # Calculate totals
        total_paid = sum(inv.total for inv in invoices if inv.status == 'paid')
        total_pending = sum(inv.total for inv in invoices if inv.status in ['pending', 'overdue'])
        
        results.append(f"Total Paid: ${total_paid:.2f}")
        results.append(f"Outstanding: ${total_pending:.2f}\n")
        
        for inv in invoices:
            data = _format_invoice(inv)
            status_emoji = {
                'paid': '✓',
                'pending': '⏳',
                'overdue': '⚠️',
                'refunded': '↩️',
                'cancelled': '✗',
            }.get(inv.status, '')
            
            results.append(
                f"\n**Invoice #{data['invoice_number']}** {status_emoji}\n"
                f"- Status: {data['status']}\n"
                f"- Total: {data['total']} {data['currency']}\n"
                f"- Due Date: {data['due_date']}\n"
                f"- Paid Date: {data['paid_date']}"
            )
        
        logger.info(f"Invoice lookup successful for {customer_email}")
        return '\n'.join(results)
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found for invoice lookup: {customer_email}")
        return f"No customer found with email: {customer_email}"
        
    except Exception as e:
        logger.error(f"Invoice lookup failed: {e}")
        return f"Error looking up invoices: {str(e)}"

