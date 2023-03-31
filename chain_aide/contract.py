from functools import wraps, partial
from typing import TYPE_CHECKING

from web3._utils.abi import filter_by_name
from web3.contract.contract import ContractFunction

from chain_aide.utils import contract_call, contract_transaction

if TYPE_CHECKING:
    from chain_aide import Aide


class Contract:
    """ 简化合约操作
    """

    def __init__(self,
                 aide: "Aide",
                 abi,
                 bytecode=None,
                 address=None,
                 ):
        self.aide = aide
        self.abi = abi
        self.bytecode = bytecode
        self.address = address
        self.origin = self.aide.web3.eth.contract(address=self.address, abi=self.abi, bytecode=self.bytecode)
        self.functions = self.origin.functions
        self.events = self.origin.events
        self._set_functions(self.origin.functions)
        self._set_events(self.origin.events)
        self._set_fallback(self.origin.fallback)

    def _set_functions(self, functions):
        """ 包装合约方法，
        """
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
        abis = filter_by_name(func.fn_name, self.abi)
        if len(abis) == 0:
            raise ValueError('The method ABI is not found.')

        # todo：优化重载方法
        abi = abis[0]

        if abi.get('stateMutability') in ['view', 'pure']:
            return contract_call(func)
        else:
            return partial(contract_transaction(func), self)

    @staticmethod
    def _event_wrap(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func().process_receipt(*args, **kwargs)

        return wrapper

    @staticmethod
    def _fallback_wrap(func):
        return contract_transaction()(func)
