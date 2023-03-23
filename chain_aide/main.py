import time
from typing import Literal

from loguru import logger
from web3.main import get_default_modules
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address, combomethod
from chain_aide.transfer import Transfer
from chain_aide.contract import Contract
from chain_aide.utils import get_web3


def get_modules(exclude: list = None):
    """ 排除节点关闭的API
    """
    if not exclude:
        exclude = []

    modules = get_default_modules()
    if 'admin' in exclude:
        modules['node'][1].pop('admin')
    if 'debug' in exclude:
        modules.pop('debug')

    return modules


class Aide:
    """ 主类，功能如下：
    1. 各个子模块的集合体，通过它来调用子模块发送交易
    2. 持有设置数据，如：默认交易账户、经济模型数据、返回结果类型等
    3. 包含一些常用方法，如：创建账户、等待块高/周期、区块解码等
    """

    def __init__(self, uri: str):
        """
        Args:
            uri: 节点开放的RPC链接
        """
        self.uri = uri
        self.default_account: LocalAccount = None  # 发送签名交易时适用的默认地址
        self.result_type = 'auto'  # 交易返回的结果类型，包括：auto, txn, hash, receipt
        # web3相关设置
        self.web3 = get_web3(uri)
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.chain_id = self.web3.eth.chain_id
        self.account = Account()
        # 设置模块
        self.__init_web3__()
        self.__init_module__()

    def __init_web3__(self):
        """ 设置web相关模块
        """
        self.eth = self.web3.eth
        self.txpool = self.web3.geth.txpool
        self.personal = self.web3.geth.personal
        self.admin = self.web3.geth.admin

    def __init_module__(self):
        self.transfer = Transfer(self)
        self.contract = Contract(self)

    @combomethod
    def create_account(self, is_hd=False):
        """ 创建账户
        """
        self.account._use_unaudited_hdwallet_features = is_hd
        return Account.create()

    @combomethod
    def create_keystore(self, passphrase, key=None):
        """ 创建钱包文件
        """
        pass

    def set_default_account(self, account: LocalAccount):
        """ 设置发送交易的默认账户
        """
        self.default_account = account

    def set_result_type(self,
                        result_type: Literal['auto', 'txn', 'hash', 'receipt']
                        ):
        """ 设置返回结果类型，建议设置为auto
        """
        self.result_type = result_type

    def send_transaction(self, txn: dict, private_key=None):
        """ 签名交易并发送，返回交易hash
        """
        if not private_key and self.default_account:
            private_key = self.default_account.key

        if not txn.get('nonce'):
            account = self.eth.account.from_key(private_key)
            txn['nonce'] = self.eth.get_transaction_count(account.address)

        signed_txn = self.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.eth.send_raw_transaction(signed_txn.rawTransaction)
        return bytes(tx_hash).hex()

    def wait_block(self, to_block, time_out=None):
        """ 等待块高
        """
        current_block = self.eth.block_number
        time_out = time_out or (to_block - current_block) * 3

        for i in range(time_out):
            time.sleep(1)
            current_block = self.eth.block_number

            if i % 10 == 0:
                logger.info(f'waiting block: {current_block} -> {to_block}')

            # 等待确定落链
            if current_block > to_block:
                logger.info(f'waiting block: {current_block} -> {to_block}')
                return

        raise TimeoutError('wait block timeout!')

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

    # def ec_recover(self, block_identifier):
    #     """ 使用keccak方式，解出区块的签名节点公钥
    #     """
    #     block = self.web3.eth.get_block(block_identifier)
    #
    #     extra = block.proofOfAuthorityData[:32]
    #     sign = block.proofOfAuthorityData[32:]
    #     raw_data = [bytes.fromhex(remove_0x_prefix(block.parentHash.hex())),
    #                 to_canonical_address(block.miner),
    #                 bytes.fromhex(remove_0x_prefix(block.stateRoot.hex())),
    #                 bytes.fromhex(remove_0x_prefix(block.transactionsRoot.hex())),
    #                 bytes.fromhex(remove_0x_prefix(block.receiptsRoot.hex())),
    #                 bytes.fromhex(remove_0x_prefix(block.logsBloom.hex())),
    #                 block.number,
    #                 block.gasLimit,
    #                 block.gasUsed,
    #                 block.timestamp,
    #                 extra,
    #                 bytes.fromhex(remove_0x_prefix(block.nonce.hex()))
    #                 ]
    #     hash_bytes = HexBytes(keccak(rlp.encode(raw_data)))
    #     signature_bytes = HexBytes(sign)
    #     signature_bytes_standard = to_standard_signature_bytes(signature_bytes)
    #     signature = Signature(signature_bytes=signature_bytes_standard)
    #     return remove_0x_prefix(HexStr(signature.recover_public_key_from_msg_hash(hash_bytes).to_hex()))
