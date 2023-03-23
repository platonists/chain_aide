import warnings
import sys
from copy import copy

from functools import wraps, partial
from web3._utils.abi import filter_by_name
from web3.contract.contract import ContractFunction
from web3.types import ABI
from eth_typing import HexStr, AnyAddress

from chain_aide.base.module import Module
from chain_aide.utils import contract_call, contract_transaction


class Contract(Module):
    abi: ABI = None
    bytecode: HexStr = None
    address: AnyAddress = None

    def init(self,
             abi,
             bytecode=None,
             address=None,
             ):
        self.__build_contract(abi, bytecode, address)
        return copy(self)

    def deploy(self,
               abi,
               bytecode,
               txn=None,
               private_key=None,
               *init_args,
               **init_kwargs):
        if self.address:
            warnings.warn(f'contract {self.address} already exists, it will be replaced.', RuntimeWarning)

        _temp_origin = self.aide.web3.eth.contract(abi=abi, bytecode=bytecode)
        txn = _temp_origin.constructor(*init_args, **init_kwargs).build_transaction(txn)
        tx_hash = self.aide.send_transaction(txn, private_key)
        receipt = self.aide.eth.wait_for_transaction_receipt(tx_hash, timeout=20)

        address = receipt.get('contractAddress')
        if not address:
            raise Exception(f'deploy contract failed, because: {receipt}.')

        self.__build_contract(abi, bytecode, address)

        return copy(self)

    def __build_contract(self,
                         abi,
                         bytecode=None,
                         address=None,
                         ):
        self.abi = abi
        self.bytecode = bytecode
        self.address = address
        self._origin = self.aide.web3.eth.contract(address=self.address, abi=self.abi, bytecode=self.bytecode)
        self.functions = self._origin.functions
        self.events = self._origin.events
        self._set_functions(self._origin.functions)
        self._set_events(self._origin.events)
        self._set_fallback(self._origin.fallback)

    def _set_functions(self, functions):
        # 合约event和function不会重名，因此不用担心属性已存在
        for func in functions:
            warp_function = self._function_wrap(getattr(functions, func))
            setattr(self, func, warp_function)

    def _set_events(self, events):
        # 合约event和function不会重名，因此不用担心属性已存在
        for event in events:
            # 通过方法名获取方法
            warp_event = self._event_wrap(event)
            setattr(self, event.event_name, warp_event)

    def _set_fallback(self, fallback):
        if type(fallback) is ContractFunction:
            warp_fallback = self._fallback_wrap(fallback)
            setattr(self, fallback, warp_fallback)
        else:
            self.fallback = fallback

    def _function_wrap(self, func):
        fn_abis = filter_by_name(func.fn_name, self.abi)
        if len(fn_abis) == 0:
            raise ValueError('The method ABI is not found.')

        # 对于重载方法，仅取其一个，但需要其方法类型相同
        # todo: 此处理存在隐患
        fn_abi = fn_abis[0]
        for _abi in fn_abis:
            if _abi.get('stateMutability') != fn_abi.get('stateMutability'):
                raise ValueError('override method are of different types')

        # 忽略首个参数 'self'，以适配公共合约包装类
        def fit_func(__self__, *args, **kwargs):
            return func(*args, **kwargs)

        if fn_abi.get('stateMutability') in ['view', 'pure']:
            return partial(contract_call(fit_func), self)
        else:
            return partial(contract_transaction()(fit_func), self)

    @staticmethod
    def _event_wrap(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func().process_receipt(*args, **kwargs)

        return wrapper

    @staticmethod
    def _fallback_wrap(func):
        return contract_transaction()(func)