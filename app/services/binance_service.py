
from binance.client import Client
from app.core.config import settings
from app.schemas import order_schema

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

def get_position_info(testnet: bool = False) -> list[order_schema.PositionInfo]:
    """ 현재 진입한 선물 포지션 정보만 필터링하여 반환합니다. """
    client = get_binance_client(testnet)
    positions = client.futures_position_information()
    # 포지션 수량이 0이 아닌 (실제 진입한) 포지션만 필터링
    active_positions = [p for p in positions if float(p['positionAmt']) != 0]
    return [order_schema.PositionInfo.model_validate(p) for p in active_positions]

def get_futures_account_balance(testnet: bool = False) -> order_schema.FuturesAccountInfo:
    """ 선물 계좌의 자산 정보 중 잔고가 0보다 큰 자산만 필터링하여 반환합니다. """
    client = get_binance_client(testnet)
    account_info = client.futures_account()
    
    # 자산 정보 중 지갑 잔고가 0보다 큰 자산만 필터링
    filtered_assets = [asset for asset in account_info['assets'] if float(asset['walletBalance']) > 0]
    account_info['assets'] = filtered_assets
    
    return order_schema.FuturesAccountInfo.model_validate(account_info)

def get_exchange_info() -> order_schema.ExchangeInfo:
    """ 거래소의 선물 심볼 중 거래 가능한 심볼 정보만 필터링하여 반환합니다. """
    client = get_binance_client()
    exchange_info = client.get_exchange_info()
    
    # 선물(USDT-M) 시장의 거래 가능한(TRADING) 심볼만 필터링
    futures_symbols = [
        s for s in exchange_info['symbols'] 
        if s.get('contractType') == 'PERPETUAL' and s.get('status') == 'TRADING'
    ]
    return order_schema.ExchangeInfo(symbols=futures_symbols)

def get_open_orders(symbol: str | None = None, testnet: bool = False) -> list[order_schema.OpenOrderInfo]:
    """ 미체결 주문 내역을 스키마에 맞게 반환합니다. """
    client = get_binance_client(testnet)
    params = {"symbol": symbol} if symbol else {}
    open_orders = client.get_open_orders(**params)
    return [order_schema.OpenOrderInfo.model_validate(o) for o in open_orders]
