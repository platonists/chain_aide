# chain-aide
它是一个能够帮助您快速访问各个主流区块链(目前仅支持eth)并使用其功能的小助手 


# 安装方法
```shell
pip install chain_aide
```


# 使用方法

```python
from eth_account import Account
from chain_aide import Aide

uri = 'http://192.168.120.121:6789'
aide = Aide(uri)

# 调用以太坊接口
print(aide.web3.clientVersion)
print(aide.web3.eth.block_number)

# 设置默认账户  
account = Account.from_key('f51ca759562e1daf9e5302d121f933a8152915d34fcbc27e542baf256b5e4b74')
aide.set_default_account(account)

"""
指定账户
"""
# 使用设置好的默认账户发送交易
to_account = Account.create()
print(aide.transfer(to_account.address, 10 * 10 ** 18))

# 使用私钥发送交易,比默认账户有更高的优先级
private_key = 'f51ca759562e1daf9e5302d121f933a8152915d34fcbc27e542baf256b5e4b74'
print(aide.transfer(to_account.address, 10 * 10 ** 18, private_key=private_key))


"""
发送转账交易
"""
# 发送转账交易，自定义
txn = {'gas': 21000, 'gasPrice': 1 * 10 ** 9, 'nonce': 100}
to_account = Account.create()
print(aide.transfer(to_account.address, 10 * 10 ** 18, txn=txn))

"""
发送合约交易
"""
abi = [{"anonymous": False, "inputs": [{"indexed": False, "internalType": "uint256", "name": "_chainId", "type": "uint256"}], "name": "_putChainID", "type": "event"}, {"inputs": [], "name": "getChainID", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "putChainID", "outputs": [], "stateMutability": "nonpayable", "type": "function"}]
bytecode = '608060405234801561001057600080fd5b50610107806100206000396000f3fe6080604052348015600f57600080fd5b506004361060325760003560e01c806336319ab0146037578063564b81ef14603f575b600080fd5b603d6059565b005b60456099565b6040516050919060ae565b60405180910390f35b466000819055507f68e891aec7f9596d6e192c48cb82364ec392d423bce80abd6e1ee5ad05860256600054604051608f919060ae565b60405180910390a1565b600046905090565b60a88160c7565b82525050565b600060208201905060c1600083018460a1565b92915050565b600081905091905056fea264697066735822122037a1668252253271128182c71109922cb1e300fb08a7080a0587f360df4071ba64736f6c63430008060033'

# 部署新的合约
contract = aide.deploy_contract(abi=abi, bytecode=bytecode)
print(contract.address)

# 已有合约，直接初始化
contract_address = '0x'
contract = aide.init_contract(abi=abi, address=contract_address)
print(contract.address)

# call调用
print(contract.getChainID())

# 发送交易(像call调用一样简答)
res = contract.putChainID()

# 解析event
print(contract.PutChainID(res))
```

