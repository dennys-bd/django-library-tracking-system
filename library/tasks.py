from datetime import date

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Loan


@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject="Book Loaned Successfully",
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Loan.DoesNotExist:
        pass


@shared_task
def check_overdue_loans():
    today = date.today()
    due_loans = Loan.objects.filter(
        is_returned=False, due_date__gt=today
    ).select_related("member__user", "book")
    for loan in due_loans:
        send_mail(
            subject="Due Loan",
            message=f'Hello {loan.member.user.username},\n\nYour loan of "{loan.book.title}" is due.\nPlease return it.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[loan.member.user.email],
            fail_silently=False,
        )
