# app/handlers/payments_rk.py
# Точка расширения под Robokassa в рамках aiogram-роутера.
# В этом пред-рекуррентном режиме отдельная логика не нужна,
# вся оплата идёт через ссылки и подтверждается в PaymentService/check_payment.
# Вебхуки ResultURL/Success/Fail у тебя обрабатываются на стороне web-сервиса.

from aiogram import Router

router = Router()
