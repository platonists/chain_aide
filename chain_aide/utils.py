import functools

from web3 import Web3, HTTPProvider, WebsocketProvider, IPCProvider
from web3._utils.threads import Timeout


def get_web3(uri, chain_id=None, hrp=None, timeout=10, modules=None) -> Web3:
    """ 通过rpc uri，获取web3对象
    """
    if uri.startswith('http'):
        provider = HTTPProvider
    elif uri.startswith('ws'):
        provider = WebsocketProvider
    elif uri.startswith('ipc'):
        provider = IPCProvider
    else:
        raise ValueError(f'unidentifiable uri {uri}')

    with Timeout(timeout) as t:
        while True:
            web3 = Web3(provider(uri), modules=modules)
            if web3.is_connected():
                break
            t.sleep(1)

    return web3


def contract_call(func):
    """ 合约调用的包装类
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs).call()

    return wrapper


def contract_transaction(func):
    """ 合约交易的包装类
    """
    @functools.wraps(func)
    def wrapper(self, *args, txn: dict = None, private_key=None, **kwargs):
        # 填充from地址，以免合约交易在预估gas时检验地址失败
        txn = txn or {}
        if not txn.get('from'):
            account = self.aide.eth.account.from_key(private_key, hrp=self.aide.hrp) if private_key else self.aide.default_account
            if account:
                txn['from'] = account.address

        txn = func(*args, **kwargs).build_transaction(txn)
        return self.aide.send_transaction(txn, private_key=private_key)

    return wrapper
