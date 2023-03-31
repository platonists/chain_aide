import time
from typing import Literal

from loguru import logger
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address, combomethod, remove_0x_prefix, to_canonical_address, keccak
from chain_aide.contract import Contract
from chain_aide.utils import get_web3


class Aide:
    """ 区块链接入助手，目前仅支持eth
    """
    transferGas: int = 21000
    account = Account()

    def __init__(self, uri: str):
        """
        Args:
            uri: 节点RPC链接
        """
        self.uri = uri
        self.default_account: LocalAccount = None  # 发送签名交易时适用的默认地址
        self.result_type = 'receipt'  # 交易返回的结果类型，包括：txn, hash, receipt
        # web3相关设置
        self.web3 = get_web3(uri)
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.chain_id = self.web3.eth.chain_id

        # 设置模块
        self.__init_web3__()

    def __init_web3__(self):
        """ 设置web相关模块
        """
        self.eth = self.web3.eth
        self.txpool = self.web3.geth.txpool
        self.personal = self.web3.geth.personal
        self.admin = self.web3.geth.admin

    @combomethod
    def to_checksum_address(self, address):
        """ 任意地址转换为checksum地址
        """
        return to_checksum_address(address)

    @combomethod
    def to_base58_address(self, address):
        """ 任意地址转换为形式的base58地址
        注意：非标准base58地址
        """
        pass

    def set_default_account(self, account: LocalAccount):
        """ 设置发送交易的默认账户
        """
        self.default_account = account

    def set_result_type(self,
                        result_type: Literal['txn', 'hash', 'receipt']
                        ):
        """ 设置返回结果类型，建议设置为auto
        """
        self.result_type = result_type

    @combomethod
    def create_account(self, is_hd=False):
        """ 创建账户
        """
        self.account._use_unaudited_hdwallet_features = is_hd
        return self.account.create()

    # @combomethod
    # def create_keystore(self, passphrase, key=None):
    #     """ 创建钱包文件
    #     """
    #     pass

    def transfer(self, to_address, amount, txn=None, private_key=None):
        """ 发送转账交易
        """
        base_txn = {
            "to": to_address,
            "gasPrice": self.eth.gas_price,
            "gas": self.transferGas,
            "data": '',
            "chainId": self.chain_id,
            "value": amount,
        }

        if txn:
            base_txn.update(txn)

        return self.send_transaction(base_txn, private_key=private_key)

    def get_balance(self, address, block_identifier=None):
        """ 查询自由金额的余额
        """
        return self.eth.get_balance(address, block_identifier)

    def init_contract(self,
                      abi,
                      bytecode=None,
                      address=None
                      ):
        return Contract(self, abi, bytecode, address)

    def deploy_contract(self,
                        abi,
                        bytecode,
                        txn=None,
                        private_key=None,
                        *init_args,
                        **init_kwargs):
        contract = self.web3.eth.contract(abi=abi, bytecode=bytecode)
        txn = contract.constructor(*init_args, **init_kwargs).build_transaction(txn)
        receipt = self.send_transaction(txn, result_type='receipt', private_key=private_key)
        address = receipt.get('contractAddress')

        if not address:
            raise Exception(f'deploy contract failed, transaction receipt: {receipt}.')

        return self.init_contract(abi, bytecode, address)

    def send_transaction(self, txn: dict, result_type=None, private_key=None):
        """ 签名交易并发送，返回交易hash
        """
        result_type = result_type or self.result_type

        if private_key:
            account = self.eth.account.from_key(private_key)
        else:
            account = self.default_account

        if not txn.get('from'):
            txn['from'] = account.address

        if not txn.get('nonce'):
            txn['nonce'] = self.eth.get_transaction_count(account.address)

        signed_txn = self.eth.account.sign_transaction(txn, account.key)
        if result_type == "txn":
            return signed_txn

        tx_hash = self.eth.send_raw_transaction(signed_txn.rawTransaction)
        if result_type == 'hash':
            return tx_hash

        receipt = self.get_transaction_receipt(tx_hash)
        if result_type == 'receipt':
            return receipt

        raise ValueError(f'unknown result type {self.result_type}')

    def get_transaction_receipt(self, tx_hash, timeout=20):
        """ 发送签名交易，并根据结果类型获取交易结果
        """
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        if type(receipt) is bytes:
            receipt = receipt.decode('utf-8')

        return receipt

    def wait_block(self, to_block, timeout=None):
        """ 等待块高
        """
        current_block = self.eth.block_number
        timeout = timeout or (to_block - current_block) * 3

        for i in range(timeout):
            time.sleep(1)
            current_block = self.eth.block_number

            if i % 10 == 0:
                logger.info(f'waiting block: {current_block} -> {to_block}')

            # 等待确定落链
            if current_block > to_block:
                logger.info(f'waiting block: {current_block} -> {to_block}')
                return

        raise TimeoutError('wait block timeout!')
