from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.tests.domain.entities.test_payment import make_payment
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository
from app.modules.payments.application.use_cases.create_payment_use_case import CreatePaymentUseCase

class FailingPaymentRepository(PaymentRepositoryPort):
    def get_payment_by_id(self, payment_id: str) -> Payment | None:
        return None

    def create_payment(self, payment: Payment) -> Payment | None:
        return None

class TestPaymentCreate:
    def test_returns_payment_when_creation_succeeds(self):
        payment_repository = InMemoryPaymentRepository()

        create_payment_use_case = CreatePaymentUseCase(payment_repository_port=payment_repository)

        # Save a new payment using the use case
        payment = create_payment_use_case.execute(make_payment())

        # verify that the payment was created and returned
        assert payment is not None
        assert payment.id is not None

        # Get payment from the repository to verify it was saved
        saved_payment = payment_repository.get_payment_by_id(payment.id)

        # verify that the saved payment matches the created payment
        assert saved_payment is not None
        assert saved_payment == payment

    def test_returns_none_when_creation_fails(self):
        payment_repository = FailingPaymentRepository()

        create_payment_use_case = CreatePaymentUseCase(payment_repository_port=payment_repository)

        # Attempt to save a payment against a repository that always fails to persist
        payment = create_payment_use_case.execute(make_payment())

        assert payment is None
