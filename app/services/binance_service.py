
from binance.client import Client
from app.core.config import settings

def get_binance_client(testnet: bool = False) -> Client:
    if testnet:
        api_key = settings.BINANCE_TESTNET_API_KEY
        api_secret = settings.BINANCE_TESTNET_API_SECRET
        tld = 'com'
    else:
        api_key = settings.BINANCE_API_KEY
        api_secret = settings.BINANCE_API_SECRET
        tld = 'com'
    
    client = Client(api_key, api_secret, tld=tld, testnet=testnet)
    return client

def get_account_info(testnet: bool = False):
    client = get_binance_client(testnet)
    return client.get_account()

def get_position_info(testnet: bool = False):
    client = get_binance_client(testnet)
    return client.get_position_risk()

def get_futures_account_balance(testnet: bool = False):
    """ 선물 계좌의 자산 및 마진 정보를 조회합니다. """
    client = get_binance_client(testnet)
    return client.futures_account_balance()

def get_exchange_info():
    """ 거래소의 모든 심볼에 대한 거래 규칙 정보를 조회합니다. """
    client = get_binance_client() # 거래 규칙은 테스트넷/메인넷 동일
    return client.get_exchange_info()

def get_open_orders(symbol: str | None = None, testnet: bool = False):
    """ 미체결 주문 내역을 조회합니다. 특정 심볼을 지정할 수 있습니다. """
    client = get_binance_client(testnet)
    return client.get_open_orders(symbol=symbol)
