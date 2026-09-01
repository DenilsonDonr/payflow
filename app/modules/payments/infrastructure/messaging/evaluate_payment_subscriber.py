import logging

from app.modules.payments.application.use_cases.evaluate_payment_use_case import (
    EvaluatePaymentUseCase,
)
from app.modules.payments.domain.exceptions.invalid_verdict import InvalidVerdictError
from app.modules.payments.domain.value_objects.verdict import Verdict
from app.shared.messaging.contracts.payment_verdict_message import PaymentVerdictMessage

logger = logging.getLogger(__name__)


class EvaluatePaymentSubscriber:
    def __init__(self, evaluate_payment_use_case: EvaluatePaymentUseCase):
        self.evaluate_payment_use_case = evaluate_payment_use_case

    def handle(self, message: PaymentVerdictMessage) -> None:
        try:
            Verdict(message.verdict)
        except InvalidVerdictError:
            logger.warning(
                "Unrecognized verdict %r for payment %s; leaving payment in PENDING.",
                message.verdict,
                message.payment_id,
            )
            return

        self.evaluate_payment_use_case.execute(
            payment_id=message.payment_id,
            verdict=message.verdict,
        )
