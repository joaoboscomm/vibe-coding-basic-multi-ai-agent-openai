"""
Management command to seed the database with sample data.
"""
from django.core.management.base import BaseCommand

from scripts.seed_data import main as seed_main


class Command(BaseCommand):
    help = 'Seed the database with sample customers, subscriptions, and knowledge base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-kb',
            action='store_true',
            help='Skip knowledge base seeding (useful if no OpenAI API key)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...\n')
        
        if options['skip_kb']:
            self.stdout.write(
                self.style.WARNING('Skipping knowledge base (--skip-kb flag set)')
            )
            # Run without KB
            from scripts.seed_data import (
                create_customers, 
                create_subscriptions, 
                create_invoices,
                create_sample_tickets
            )
            from django.db import transaction
            
            with transaction.atomic():
                customers = create_customers()
                subscriptions = create_subscriptions(customers)
                create_invoices(customers, subscriptions)
                create_sample_tickets(customers)
        else:
            seed_main()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded the database!')
        )

