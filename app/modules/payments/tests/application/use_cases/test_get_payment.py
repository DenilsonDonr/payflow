from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.application.use_cases.get_payment_use_case import GetPaymentUseCase
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository
from app.modules.payments.tests.domain.entities.test_payment import make_payment

class TestPaymentGet:
    def test_returns_payment_when_it_exists(self):
        # instance memory payment
        payment_repository = InMemoryPaymentRepository()
        
        # Make test in memory payment repository and add a payment to it 
        for i in range(1, 4):
            payment = make_payment(id=f"UUID-000{i}")
            payment_repository.add(payment)
        
        # Create the use case instance
        get_payment_use_case = GetPaymentUseCase(payment_repository_port=payment_repository)

        # Test getting an existing payment
        payment_id = "UUID-0003"
        payment = get_payment_use_case.execute(payment_id)
        
        print(f"Retrieved payment: {payment}")
        
        assert isinstance(payment, Payment)
        assert payment is not None
        assert payment.id == payment_id
        
    def test_returns_none_when_payment_does_not_exist(self):
        # instance memory payment
        payment_repository = InMemoryPaymentRepository()
        
        # Make test in memory payment repository and add a payment to it 
        for i in range(1, 4):
            payment = make_payment(id=f"UUID-000{i}")
            payment_repository.add(payment)
        
        # Create the use case instance
        get_payment_use_case = GetPaymentUseCase(payment_repository_port=payment_repository)

        # Test getting a non-existing payment
        payment_id = "UUID-9999"
        payment = get_payment_use_case.execute(payment_id)
        
        assert not isinstance(payment, Payment)
        assert payment is None