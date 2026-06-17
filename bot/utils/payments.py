"""Payment processing utilities for VPN Bot (Fully Async with aiohttp)"""

import logging
import hashlib
import json
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import aiohttp

from bot.config.settings import Config

logger = logging.getLogger(__name__)

class PaymentError(Exception):
    """Custom payment processing error"""
    pass

class YooMoneyPayment:
    """YooMoney payment processor using Quickpay Forms & History API"""

    def __init__(self):
        self.token = Config.YOOMONEY_TOKEN
        # Добавь YOOMONEY_WALLET в свой Config (номер кошелька, например, 41001...)
        self.wallet = getattr(Config, 'YOOMONEY_WALLET', None)
        self.base_url = "https://yoomoney.ru/api"

    def create_payment(self, amount: int, order_id: str, description: str) -> Dict[str, Any]:
        """
        Create YooMoney Quickpay payment link.
        Doesn't require API requests, generates URL instantly.
        """
        if not self.wallet:
            raise PaymentError("Не настроен номер кошелька ЮMoney (YOOMONEY_WALLET)")

        try:
            amount_rub = amount / 100  # Переводим копейки в рубли

            # Параметры формы быстрой оплаты ЮMoney Quickpay
            params = {
                'receiver': self.wallet,
                'quickpay-form': 'button',
                'targets': description,
                'paymentType': 'SB',  # SB = СБП/Карты, PC = ЮMoney кошелек
                'sum': f"{amount_rub:.2f}",
                'label': order_id,  # Уникальный ID платежа для проверки статуса
            }

            # Строим query-строку вручную
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            payment_url = f"https://yoomoney.ru/quickpay/confirm.xml?{query_string}"

            return {
                'payment_id': order_id,  # Для Quickpay ID платежа — это наш order_id
                'payment_url': payment_url,
                'amount': amount,
                'expires_at': datetime.now(timezone.utc) + timedelta(minutes=15)
            }
        except Exception as e:
            logger.error(f"YooMoney payment generation error: {e}")
            raise PaymentError("Ошибка создания ссылки на оплату YooMoney")

    async def check_payment(self, payment_id: str) -> str:
        """Check YooMoney payment status asynchronously via History API"""
        if not self.token:
            return 'unknown'

        try:
            url = f"{self.base_url}/operation-history"
            # Ищем операцию по ярлыку (label), который равен нашему payment_id (order_id)
            data = {
                'type': 'deprecation',  # Получение переводов
                'label': payment_id,
                'records': 1
            }
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"YooMoney API returned status {response.status}")
                        return 'unknown'

                    result = await response.json()
                    operations = result.get('operations', [])

                    if not operations:
                        return 'pending'

                    op = operations[0]
                    # Проверяем, что платеж успешно проведен (success)
                    if op.get('status') == 'success':
                        return 'completed'

                    return 'pending'

        except Exception as e:
            logger.error(f"YooMoney async payment check error: {e}")
            return 'unknown'

class QiwiPayment:
    """QIWI payment processor (DEPRECATED - QIWI is closed)"""

    def __init__(self):
        pass

    def create_payment(self, amount: int, order_id: str, description: str) -> Dict[str, Any]:
        logger.error("QIWI payment attempted but QIWI service is dead since 2024.")
        raise PaymentError("Оплата через QIWI временно недоступна. Выберите другой метод.")

    async def check_payment(self, payment_id: str) -> str:
        return 'failed'

class CryptomusPayment:
    """Cryptomus cryptocurrency payment processor (Async)"""

    def __init__(self):
        self.api_key = Config.CRYPTOMUS_API_KEY
        self.merchant_id = Config.CRYPTOMUS_MERCHANT_ID
        self.base_url = "https://api.cryptomus.com/v1"

    def _generate_signature(self, data: dict) -> str:
        """
        Generate correct signature for Cryptomus API.
        Formula: md5(base64(json_data) + api_key)
        """
        # Превращаем dict в строку JSON без лишних пробелов
        json_data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        # Кодируем в Base64
        b64_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        # Складываем Base64 строку и API-ключ, затем берем MD5
        signature = hashlib.md5((b64_data + self.api_key).encode('utf-8')).hexdigest()
        return signature

    async def create_payment(self, amount: int, order_id: str, description: str) -> Dict[str, Any]:
        """Create cryptocurrency payment asynchronously"""
        try:
            url = f"{self.base_url}/payment"

            data = {
                'amount': f"{amount / 100:.2f}",  # Конвертируем в рубли (копейки / 100)
                'currency': 'RUB',
                'order_id': order_id,
                'merchant': self.merchant_id,
                'url_callback': 'https://your-domain.com/webhook/cryptomus',  # Настрой вебхук, если нужен
                'url_return': 'https://t.me/your_bot',
                'lifetime': 900,  # 15 минут
                'to_currency': 'USDT'
            }

            headers = {
                'merchant': self.merchant_id,
                'sign': self._generate_signature(data),
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    result = await response.json()

                    if result.get('state') == 0:  # Success
                        payment_data = result.get('result', {})
                        return {
                            'payment_id': payment_data.get('uuid'),
                            'payment_url': payment_data.get('url'),
                            'amount': amount,
                            'expires_at': datetime.now(timezone.utc) + timedelta(minutes=15)
                        }
                    else:
                        raise PaymentError(f"Cryptomus error: {result.get('message')}")

        except aiohttp.ClientError as e:
            logger.error(f"Cryptomus Async API error: {e}")
            raise PaymentError("Ошибка подключения к Cryptomus")
        except Exception as e:
            logger.error(f"Cryptomus payment creation error: {e}")
            raise PaymentError("Ошибка создания криптоплатежа")

    async def check_payment(self, payment_id: str) -> str:
        """Check cryptocurrency payment status asynchronously"""
        try:
            url = f"{self.base_url}/payment/info"
            data = {
                'merchant': self.merchant_id,
                'uuid': payment_id
            }

            headers = {
                'merchant': self.merchant_id,
                'sign': self._generate_signature(data),
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    result = await response.json()

                    if result.get('state') == 0:
                        payment_data = result.get('result', {})
                        status = payment_data.get('payment_status')

                        if status == 'paid':
                            return 'completed'
                        elif status in ['fail', 'cancel', 'system_fail']:
                            return 'failed'
                        else:
                            return 'pending'

                    return 'unknown'

        except Exception as e:
            logger.error(f"Cryptomus payment check error: {e}")
            return 'unknown'

class PaymentManager:
    """Main payment manager class (Async ready)"""

    def __init__(self):
        self.yoomoney = YooMoneyPayment() if Config.YOOMONEY_TOKEN else None
        self.qiwi = QiwiPayment() if Config.QIWI_TOKEN else None
        self.cryptomus = CryptomusPayment() if Config.CRYPTOMUS_API_KEY else None

    async def create_payment(self, method: str, amount: int, order_id: str, description: str) -> Dict[str, Any]:
        """Create payment with specified method (Async wrapper)"""
        try:
            if method == 'yoomoney' and self.yoomoney:
                # Генерация ссылки быстрая, но для единообразия интерфейса держим её асинхронной
                return self.yoomoney.create_payment(amount, order_id, description)
            elif method == 'qiwi' and self.qiwi:
                return self.qiwi.create_payment(amount, order_id, description)
            elif method == 'crypto' and self.cryptomus:
                return await self.cryptomus.create_payment(amount, order_id, description)
            else:
                raise PaymentError(f"Платежный метод {method} недоступен")

        except PaymentError:
            raise
        except Exception as e:
            logger.error(f"Payment creation error: {e}")
            raise PaymentError("Ошибка создания платежа")

    async def check_payment(self, method: str, payment_id: str) -> str:
        """Check payment status asynchronously"""
        try:
            if method == 'yoomoney' and self.yoomoney:
                return await self.yoomoney.check_payment(payment_id)
            elif method == 'qiwi' and self.qiwi:
                return await self.qiwi.check_payment(payment_id)
            elif method == 'crypto' and self.cryptomus:
                return await self.cryptomus.check_payment(payment_id)
            else:
                return 'unknown'

        except Exception as e:
            logger.error(f"Payment check error: {e}")
            return 'unknown'

    def get_available_methods(self) -> list:
        """Get list of available payment methods"""
        methods = []
        if self.yoomoney:
            methods.append('yoomoney')
        if self.cryptomus:
            methods.append('crypto')
        return methods

# Global payment manager instance
payment_manager = PaymentManager()
