import uuid

from app.modules.payments.application.use_cases.get_payment_use_case import GetPaymentUseCase
from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.tests.domain.entities.test_payment import make_payment
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository


class TestPaymentGet:
    async def test_returns_payment_when_it_exists(self):
        # instance memory payment
        payment_repository = InMemoryPaymentRepository()

        # Make test in memory payment repository and add a payment to it
        payment_ids = [uuid.uuid4() for _ in range(1, 4)]
        for payment_id in payment_ids:
            payment = make_payment(id=payment_id)
            payment_repository.add(payment)

        # Create the use case instance
        get_payment_use_case = GetPaymentUseCase(payment_repository_port=payment_repository)

        # Test getting an existing payment
        payment_id = payment_ids[2]
        payment = await get_payment_use_case.execute(payment_id)

        assert isinstance(payment, Payment)
        assert payment is not None
        assert payment.id == payment_id

    async def test_returns_none_when_payment_does_not_exist(self):
        # instance memory payment
        payment_repository = InMemoryPaymentRepository()

        # Make test in memory payment repository and add a payment to it
        for _ in range(1, 4):
            payment = make_payment(id=uuid.uuid4())
            payment_repository.add(payment)

        # Create the use case instance
        get_payment_use_case = GetPaymentUseCase(payment_repository_port=payment_repository)

        # Test getting a non-existing payment
        payment_id = uuid.uuid4()
        payment = await get_payment_use_case.execute(payment_id)

        assert not isinstance(payment, Payment)
        assert payment is None
