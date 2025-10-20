# app/services/subscription_service.py
from datetime import timedelta
from app.repositories.subscription_repo import SubscriptionRepo
from app.utils.dates import now_utc


class SubscriptionService:
    def __init__(self, subs: SubscriptionRepo):
        self.subs = subs

    async def start_or_extend(self, user_id: int, plan: str, auto_renew: bool = True):
        """
        Активирует новую или продлевает существующую подписку ОТ ТЕКУЩЕГО ВРЕМЕНИ.
        План определяет длительность:
          - m1  -> 30 дней
          - m3  -> 90 дней
          - m12 -> 365 дней
          - trial3_10 -> 3 дня (платный триал)
        """
        now = now_utc()
        add_days_map = {"m1": 30, "m3": 90, "m12": 365, "trial3_10": 3}
        add_days = add_days_map.get(plan, 30)

        is_trial = (plan == "trial3_10")
        new_expires_at = now + timedelta(days=add_days)

        return await self.subs.create_or_extend(
            user_id=user_id,
            plan=plan,
            new_expires_at=new_expires_at,
            is_trial=is_trial,
            auto_renew=auto_renew,
        )
