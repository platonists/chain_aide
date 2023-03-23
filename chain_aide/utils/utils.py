import functools
import os

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
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self, *args, **kwargs).call()

    return wrapper


# 合约交易装饰器，仅用于接受参数
def contract_transaction(default_txn=None):
    # 实际装饰器
    def decorator(func):

        @functools.wraps(func)
        def wrapper(self, *args, txn: dict = None, private_key=None, **kwargs):
            """
            """
            # 合并交易体
            if txn:
                if default_txn:
                    default_txn.update(txn)
                    txn = default_txn
            else:
                txn = default_txn if default_txn else {}

            # 填充from地址，以免合约交易在预估gas时检验地址失败
            if not txn.get('from'):
                account = self.aide.eth.account.from_key(private_key,
                                                            hrp=self.aide.hrp) if private_key else self.aide.default_account
                if account:
                    txn['from'] = account.address

            # 构造合约方法对象
            if func.__name__ == 'fit_func':
                # solidity合约方法不传入private key参数，避免abi解析问题
                fn = func(self, *args, **kwargs)
            else:
                # 内置合约有时候需要用到私钥信息，用于生成参数的默认值，如：staking
                fn = func(self, *args, private_key=private_key, **kwargs)

            # 构建合约交易体dict
            txn = fn.build_transaction(txn)

            return self._transaction_handler_(txn, private_key=private_key)

        return wrapper

    return decorator


def execute_cmd(cmd):
    r = os.popen(cmd)
    out = r.read()
    r.close()
    return out
