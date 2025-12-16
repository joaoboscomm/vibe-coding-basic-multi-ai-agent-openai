"""
Support ticket creation tool for escalation handling.
"""
import logging
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from apps.support.models import Customer, SupportTicket

logger = logging.getLogger(__name__)


def _determine_priority(description: str, category: str) -> str:
    """
    Determine ticket priority based on keywords and category.
    """
    description_lower = description.lower()
    
    # Urgent keywords
    urgent_keywords = ['urgent', 'critical', 'emergency', 'down', 'outage', 'not working at all']
    if any(kw in description_lower for kw in urgent_keywords):
        return 'urgent'
    
    # High priority keywords
    high_keywords = ['cannot access', 'blocked', 'important', 'deadline', 'losing data', 'security']
    if any(kw in description_lower for kw in high_keywords):
        return 'high'
    
    # Category-based priority
    if category in ['bug_report', 'billing']:
        return 'high'
    
    return 'medium'


@tool
def create_support_ticket(
    customer_email: str,
    subject: str,
    description: str,
    category: str = 'other',
    conversation_id: str = None,
) -> str:
    """
    Create a support ticket for human escalation.
    Use this when the customer's issue requires human intervention or cannot be resolved automatically.
    
    Args:
        customer_email: The customer's email address
        subject: Brief summary of the issue
        description: Detailed description of the problem and any troubleshooting done
        category: Issue category (billing, technical, account, feature_request, bug_report, other)
        conversation_id: Optional ID of the conversation for context
        
    Returns:
        Confirmation message with ticket details
    """
    try:
        # Validate category
        valid_categories = ['billing', 'technical', 'account', 'feature_request', 'bug_report', 'other']
        if category not in valid_categories:
            category = 'other'
        
        # Look up customer
        try:
            customer = Customer.objects.get(email=customer_email.lower().strip())
        except Customer.DoesNotExist:
            return (
                f"Cannot create ticket: No customer found with email {customer_email}. "
                "Please verify the email address."
            )
        
        # Determine priority
        priority = _determine_priority(description, category)
        
        # Create the ticket
        ticket = SupportTicket.objects.create(
            customer=customer,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            status='open',
            conversation_id=UUID(conversation_id) if conversation_id else None,
            metadata={
                'created_by': 'ai_agent',
                'escalation_reason': 'automated_escalation',
            }
        )
        
        # Determine expected response time based on priority
        response_times = {
            'urgent': '1 hour',
            'high': '4 hours',
            'medium': '24 hours',
            'low': '48 hours',
        }
        expected_response = response_times.get(priority, '24 hours')
        
        logger.info(
            f"Support ticket created: {ticket.id} for {customer_email}",
            extra={
                'ticket_id': str(ticket.id),
                'category': category,
                'priority': priority,
            }
        )
        
        return (
            f"**Support Ticket Created Successfully**\n\n"
            f"- Ticket ID: `{ticket.id}`\n"
            f"- Subject: {subject}\n"
            f"- Category: {category.replace('_', ' ').title()}\n"
            f"- Priority: {priority.title()}\n"
            f"- Expected Response: Within {expected_response}\n\n"
            f"A human support specialist will review your case and reach out to you at {customer_email}. "
            f"Please save your ticket ID for reference."
        )
        
    except Exception as e:
        logger.error(f"Failed to create support ticket: {e}", exc_info=True)
        return f"Error creating support ticket: {str(e)}. Please try again or contact support directly."

