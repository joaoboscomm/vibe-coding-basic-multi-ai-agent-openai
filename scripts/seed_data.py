"""
Seed data script for the customer support system.
Populates the database with sample customers, subscriptions, invoices,
and knowledge base documents for a SaaS project management platform (CloudFlow).

Usage:
    python manage.py shell < scripts/seed_data.py
    OR
    docker-compose exec web python manage.py shell < scripts/seed_data.py
"""
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction

from apps.support.models import Customer, Subscription, Invoice, SupportTicket
from apps.core.models import KnowledgeDocument
from rag.knowledge_base import KnowledgeBaseManager


def create_customers():
    """Create sample customers."""
    customers_data = [
        {
            'email': 'john.smith@techstartup.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'company_name': 'Tech Startup Inc',
            'phone': '+1-555-0101',
            'metadata': {'industry': 'technology', 'company_size': '10-50'},
        },
        {
            'email': 'sarah.johnson@designco.com',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'company_name': 'Design Co',
            'phone': '+1-555-0102',
            'metadata': {'industry': 'design', 'company_size': '1-10'},
        },
        {
            'email': 'michael.chen@enterprise.com',
            'first_name': 'Michael',
            'last_name': 'Chen',
            'company_name': 'Enterprise Solutions Ltd',
            'phone': '+1-555-0103',
            'metadata': {'industry': 'consulting', 'company_size': '100-500'},
        },
        {
            'email': 'emma.davis@freelancer.com',
            'first_name': 'Emma',
            'last_name': 'Davis',
            'company_name': '',
            'phone': '+1-555-0104',
            'metadata': {'industry': 'freelance', 'company_size': '1'},
        },
        {
            'email': 'david.wilson@agencyplus.com',
            'first_name': 'David',
            'last_name': 'Wilson',
            'company_name': 'Agency Plus',
            'phone': '+1-555-0105',
            'metadata': {'industry': 'marketing', 'company_size': '50-100'},
        },
    ]

    customers = []
    for data in customers_data:
        customer, created = Customer.objects.get_or_create(
            email=data['email'],
            defaults=data
        )
        customers.append(customer)
        if created:
            print(f"Created customer: {customer.email}")
        else:
            print(f"Customer exists: {customer.email}")

    return customers


def create_subscriptions(customers):
    """Create subscriptions for customers."""
    today = date.today()
    
    subscriptions_data = [
        # John - Professional monthly
        {
            'customer': customers[0],
            'plan': 'professional',
            'status': 'active',
            'billing_cycle': 'monthly',
            'price': Decimal('49.00'),
            'start_date': today - timedelta(days=180),
            'seats': 10,
            'features': ['unlimited_projects', 'team_collaboration', 'api_access', 'priority_support'],
        },
        # Sarah - Starter yearly
        {
            'customer': customers[1],
            'plan': 'starter',
            'status': 'active',
            'billing_cycle': 'yearly',
            'price': Decimal('190.00'),
            'start_date': today - timedelta(days=90),
            'seats': 3,
            'features': ['5_projects', 'basic_collaboration', 'email_support'],
        },
        # Michael - Enterprise yearly
        {
            'customer': customers[2],
            'plan': 'enterprise',
            'status': 'active',
            'billing_cycle': 'yearly',
            'price': Decimal('990.00'),
            'start_date': today - timedelta(days=365),
            'seats': 50,
            'features': ['unlimited_everything', 'sso', 'dedicated_support', 'custom_integrations', 'sla'],
        },
        # Emma - Free trial
        {
            'customer': customers[3],
            'plan': 'starter',
            'status': 'trial',
            'billing_cycle': 'monthly',
            'price': Decimal('19.00'),
            'start_date': today - timedelta(days=7),
            'trial_end_date': today + timedelta(days=7),
            'seats': 1,
            'features': ['3_projects', 'basic_features'],
        },
        # David - Professional monthly (past due)
        {
            'customer': customers[4],
            'plan': 'professional',
            'status': 'past_due',
            'billing_cycle': 'monthly',
            'price': Decimal('49.00'),
            'start_date': today - timedelta(days=120),
            'seats': 15,
            'features': ['unlimited_projects', 'team_collaboration', 'api_access'],
        },
    ]

    subscriptions = []
    for data in subscriptions_data:
        subscription, created = Subscription.objects.get_or_create(
            customer=data['customer'],
            plan=data['plan'],
            defaults=data
        )
        subscriptions.append(subscription)
        if created:
            print(f"Created subscription: {subscription.customer.email} - {subscription.plan}")

    return subscriptions


def create_invoices(customers, subscriptions):
    """Create sample invoices."""
    today = date.today()
    
    invoices_data = [
        # John's invoices
        {
            'customer': customers[0],
            'subscription': subscriptions[0],
            'invoice_number': 'INV-2024-001',
            'status': 'paid',
            'amount': Decimal('49.00'),
            'tax': Decimal('4.41'),
            'total': Decimal('53.41'),
            'due_date': today - timedelta(days=30),
            'paid_date': today - timedelta(days=28),
            'description': 'CloudFlow Professional Plan - Monthly',
        },
        {
            'customer': customers[0],
            'subscription': subscriptions[0],
            'invoice_number': 'INV-2024-002',
            'status': 'paid',
            'amount': Decimal('49.00'),
            'tax': Decimal('4.41'),
            'total': Decimal('53.41'),
            'due_date': today,
            'paid_date': today - timedelta(days=2),
            'description': 'CloudFlow Professional Plan - Monthly',
        },
        # Sarah's invoice
        {
            'customer': customers[1],
            'subscription': subscriptions[1],
            'invoice_number': 'INV-2024-003',
            'status': 'paid',
            'amount': Decimal('190.00'),
            'tax': Decimal('17.10'),
            'total': Decimal('207.10'),
            'due_date': today - timedelta(days=60),
            'paid_date': today - timedelta(days=58),
            'description': 'CloudFlow Starter Plan - Annual',
        },
        # Michael's invoices
        {
            'customer': customers[2],
            'subscription': subscriptions[2],
            'invoice_number': 'INV-2024-004',
            'status': 'paid',
            'amount': Decimal('990.00'),
            'tax': Decimal('89.10'),
            'total': Decimal('1079.10'),
            'due_date': today - timedelta(days=365),
            'paid_date': today - timedelta(days=365),
            'description': 'CloudFlow Enterprise Plan - Annual',
        },
        # David's invoice (overdue)
        {
            'customer': customers[4],
            'subscription': subscriptions[4],
            'invoice_number': 'INV-2024-005',
            'status': 'overdue',
            'amount': Decimal('49.00'),
            'tax': Decimal('4.41'),
            'total': Decimal('53.41'),
            'due_date': today - timedelta(days=15),
            'description': 'CloudFlow Professional Plan - Monthly',
        },
    ]

    invoices = []
    for data in invoices_data:
        invoice, created = Invoice.objects.get_or_create(
            invoice_number=data['invoice_number'],
            defaults=data
        )
        invoices.append(invoice)
        if created:
            print(f"Created invoice: {invoice.invoice_number}")

    return invoices


def create_knowledge_base():
    """Create knowledge base documents with embeddings."""
    documents = [
        # FAQs
        {
            'title': 'How to create a new project in CloudFlow',
            'content': '''To create a new project in CloudFlow, follow these steps:
1. Log in to your CloudFlow dashboard
2. Click the "New Project" button in the top right corner
3. Enter your project name and description
4. Select a template or start from scratch
5. Invite team members if needed
6. Click "Create Project"

Your new project will appear in your dashboard immediately. You can customize settings, add tasks, and start collaborating with your team.''',
            'category': 'faq',
        },
        {
            'title': 'Understanding CloudFlow subscription plans',
            'content': '''CloudFlow offers four subscription plans:

**Free Plan**: Perfect for individuals
- Up to 3 projects
- Basic task management
- 1 GB storage
- Email support

**Starter Plan ($19/month or $190/year)**:
- Up to 5 projects
- Basic collaboration features
- 10 GB storage
- Email support
- 3 team members

**Professional Plan ($49/month or $490/year)**:
- Unlimited projects
- Advanced collaboration
- 100 GB storage
- Priority support
- API access
- Up to 25 team members

**Enterprise Plan (Custom pricing)**:
- Everything in Professional
- SSO/SAML authentication
- Dedicated support
- Custom integrations
- Unlimited team members
- SLA guarantee''',
            'category': 'faq',
        },
        {
            'title': 'How to upgrade or downgrade my subscription',
            'content': '''To change your CloudFlow subscription:

1. Go to Settings > Billing
2. Click "Change Plan"
3. Select your new plan
4. Review the prorated charges or credits
5. Confirm the change

**Upgrading**: Your new features are available immediately. You'll be charged a prorated amount for the remainder of your billing cycle.

**Downgrading**: Changes take effect at the end of your current billing cycle. Make sure to export any data that exceeds your new plan's limits.

Need help deciding? Contact our support team for personalized recommendations.''',
            'category': 'faq',
        },
        {
            'title': 'Team collaboration and permissions in CloudFlow',
            'content': '''CloudFlow supports three permission levels:

**Admin**: Full access to all project settings, can invite/remove members, manage billing
**Editor**: Can create and edit tasks, upload files, comment on items
**Viewer**: Read-only access, can view tasks and comment but not edit

To invite team members:
1. Open your project
2. Click "Team" in the sidebar
3. Click "Invite Members"
4. Enter email addresses
5. Select permission level
6. Send invitations

Team members will receive an email invitation. They'll need to create an account if they don't have one.''',
            'category': 'documentation',
        },
        # Troubleshooting
        {
            'title': 'Troubleshooting sync issues in CloudFlow',
            'content': '''If you're experiencing sync problems:

1. **Check your internet connection**: CloudFlow requires a stable connection to sync data.

2. **Clear browser cache**: Go to your browser settings and clear cached data for CloudFlow.

3. **Try a different browser**: Sometimes browser extensions can interfere with syncing.

4. **Check CloudFlow status**: Visit status.cloudflow.com to see if there are any ongoing issues.

5. **Force refresh**: Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac) to force refresh.

6. **Log out and back in**: This refreshes your session and can resolve authentication issues.

If problems persist, contact support with:
- Your browser and version
- Operating system
- Description of the issue
- Any error messages you see''',
            'category': 'troubleshooting',
        },
        {
            'title': 'Password reset and account recovery',
            'content': '''To reset your CloudFlow password:

1. Go to cloudflow.com/login
2. Click "Forgot Password"
3. Enter your email address
4. Check your inbox for a reset link (check spam folder too)
5. Click the link and create a new password

Password requirements:
- At least 8 characters
- One uppercase letter
- One number
- One special character

If you don't receive the email:
- Check spam/junk folders
- Verify you're using the correct email
- Wait a few minutes and try again
- Contact support if problems persist

For two-factor authentication issues, contact support with proof of account ownership.''',
            'category': 'troubleshooting',
        },
        # Policies
        {
            'title': 'CloudFlow refund policy',
            'content': '''CloudFlow offers refunds under the following conditions:

**Monthly subscriptions**: 
- Full refund within 7 days of purchase
- No refund after 7 days

**Annual subscriptions**:
- Full refund within 30 days of purchase
- Pro-rated refund within the first 3 months
- No refund after 3 months

**How to request a refund**:
1. Go to Settings > Billing
2. Click "Request Refund"
3. Provide a reason (optional)
4. Submit request

Refunds are processed within 5-10 business days and credited to your original payment method.

Note: Enterprise customers should contact their account manager for refund requests.''',
            'category': 'policy',
        },
        {
            'title': 'CloudFlow data retention and deletion policy',
            'content': '''CloudFlow's data policies:

**Active accounts**:
- All data is retained as long as your account is active
- Deleted items are moved to trash for 30 days before permanent deletion

**Cancelled subscriptions**:
- Data is retained for 90 days after cancellation
- You can reactivate and recover data within this period
- After 90 days, data is permanently deleted

**Account deletion**:
- Request account deletion in Settings > Account > Delete Account
- 14-day grace period before deletion begins
- All data permanently deleted within 30 days of deletion request

**Data export**:
- Export all your data anytime in Settings > Data > Export
- Available formats: JSON, CSV
- Enterprise customers can request custom export formats''',
            'category': 'policy',
        },
        # More documentation
        {
            'title': 'Using CloudFlow API for integrations',
            'content': '''CloudFlow's API allows you to integrate with other tools.

**Getting Started**:
1. Generate an API key in Settings > API
2. Use the key in your Authorization header
3. Base URL: api.cloudflow.com/v1

**Common endpoints**:
- GET /projects - List all projects
- POST /projects - Create new project
- GET /tasks - List tasks
- POST /tasks - Create task
- PUT /tasks/:id - Update task

**Rate limits**:
- Starter: 100 requests/minute
- Professional: 1000 requests/minute
- Enterprise: Custom limits

**Documentation**: Full API docs at docs.cloudflow.com/api

Need help? Contact support or visit our developer community at community.cloudflow.com.''',
            'category': 'documentation',
        },
        {
            'title': 'CloudFlow mobile app features',
            'content': '''The CloudFlow mobile app is available for iOS and Android.

**Features**:
- View and edit projects and tasks
- Real-time notifications
- Offline mode for viewing tasks
- Quick task creation
- Time tracking
- File uploads from camera
- Voice notes

**Sync**: Changes sync automatically when connected to the internet. Offline changes sync when back online.

**Download**:
- iOS: App Store - search "CloudFlow"
- Android: Google Play - search "CloudFlow"

**Requirements**:
- iOS 14.0 or later
- Android 8.0 or later

Note: Some advanced features are only available on the web version.''',
            'category': 'documentation',
        },
    ]

    print("\nCreating knowledge base documents with embeddings...")
    kb_manager = KnowledgeBaseManager()
    
    created_count = 0
    for doc in documents:
        # Check if document already exists
        existing = KnowledgeDocument.objects.filter(title=doc['title']).first()
        if not existing:
            kb_manager.add_document(
                title=doc['title'],
                content=doc['content'],
                category=doc['category'],
            )
            print(f"Created document: {doc['title'][:50]}...")
            created_count += 1
        else:
            print(f"Document exists: {doc['title'][:50]}...")
    
    print(f"\nCreated {created_count} new knowledge base documents")
    return created_count


def create_sample_tickets(customers):
    """Create sample support tickets."""
    tickets_data = [
        {
            'customer': customers[2],  # Michael
            'subject': 'Need custom SSO integration',
            'description': 'We need to integrate CloudFlow with our company\'s OKTA SSO. Can you help set this up?',
            'category': 'technical',
            'priority': 'high',
            'status': 'in_progress',
            'assigned_to': 'enterprise-support@cloudflow.com',
        },
        {
            'customer': customers[4],  # David
            'subject': 'Payment failed - need to update card',
            'description': 'My payment failed and I need to update my credit card information. Can you help?',
            'category': 'billing',
            'priority': 'medium',
            'status': 'open',
        },
    ]

    for data in tickets_data:
        ticket, created = SupportTicket.objects.get_or_create(
            customer=data['customer'],
            subject=data['subject'],
            defaults=data
        )
        if created:
            print(f"Created ticket: {ticket.subject}")


def main():
    """Main function to seed all data."""
    print("=" * 60)
    print("CloudFlow Customer Support - Seed Data")
    print("=" * 60)

    with transaction.atomic():
        print("\n📦 Creating customers...")
        customers = create_customers()

        print("\n📋 Creating subscriptions...")
        subscriptions = create_subscriptions(customers)

        print("\n💰 Creating invoices...")
        invoices = create_invoices(customers, subscriptions)

        print("\n🎫 Creating support tickets...")
        create_sample_tickets(customers)

    # Knowledge base is created outside transaction due to API calls
    print("\n📚 Creating knowledge base...")
    create_knowledge_base()

    print("\n" + "=" * 60)
    print("✅ Seed data created successfully!")
    print("=" * 60)

    # Print summary
    print("\n📊 Summary:")
    print(f"  - Customers: {Customer.objects.count()}")
    print(f"  - Subscriptions: {Subscription.objects.count()}")
    print(f"  - Invoices: {Invoice.objects.count()}")
    print(f"  - Support Tickets: {SupportTicket.objects.count()}")
    print(f"  - Knowledge Documents: {KnowledgeDocument.objects.count()}")


if __name__ == '__main__':
    main()

