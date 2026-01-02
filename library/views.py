from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from .models import Author, Book, Loan, Member
from .serializers import (
    AuthorSerializer,
    BookSerializer,
    LoanSerializer,
    MemberSerializer,
)
from .tasks import send_loan_notification


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("author")

    @action(detail=True, methods=["post"])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response(
                {"error": "No available copies."}, status=status.HTTP_400_BAD_REQUEST
            )
        member_id = request.data.get("member_id")
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response(
                {"error": "Member does not exist."}, status=status.HTTP_400_BAD_REQUEST
            )
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response(
            {"status": "Book loaned successfully."}, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get("member_id")
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response(
                {"error": "Active loan does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response(
            {"status": "Book returned successfully."}, status=status.HTTP_200_OK
        )


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=["post"])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()
        if loan.due_date > date.today():
            return Response(
                {"error": "Loan is already overdue."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        additional_days = request.data.get("additional_days")
        if additional_days < 1:
            return Response(
                {"error": "additional_days should be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        loan.due_date += loan.due_date + timedelta(days=additional_days)
        loan.save()

        serializer = self.serializer_class(data=loan)

        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
