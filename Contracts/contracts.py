import json

from Libraries.nodes import Instance_Web3

Directory_Contracts = 'Contracts/'


def LoadContractABI(abiFileName, subdirectory=Directory_Contracts):
    with open(subdirectory + abiFileName, 'r') as abi_definition:
        return json.load(abi_definition)


def LoadContract(address, abi):
    return Instance_Web3.eth.contract(address=address, abi=abi)


Contract_DiamondLoupe = LoadContract(None, LoadContractABI("proxy_diamondLoupe.json"))

# Contract objects keyed by name
ContractsDict = {}
Contract_DiamondProxy = None


# NOTE: This is important!  With the new solidity compiler version 0.6.x, the proxy ABI will contain the following
# 	{
# 		"stateMutability": "payable",
# 		"type": "receive"
# 	},
# My version of web3.py that I'm using has issues with this. It will result in an error that looks like this:
#   File "/Users/pako/Projects/Eth/KeeperDAO/Env_Ninja_Mac/lib/python3.6/site-packages/web3/utils/abi.py", line 46, in filter_by_name
#     in contract_abi
#   File "/Users/pako/Projects/Eth/KeeperDAO/Env_Ninja_Mac/lib/python3.6/site-packages/web3/utils/abi.py", line 49, in <listcomp>
#     abi['name'] == name
# KeyError: 'name'
# To properly fix this, I should update to a newer version of web3.py, but right now I don't want to deal with that upgrade because that may break other things
# To work around this issue for now, simply remove this part of the ABI from the JSON ABI in the python code since we do not need it


def CreateNewProxyContract(address, filenameToAbi):
    global Contract_DiamondProxy

    Contract_DiamondProxy = LoadContract(
        Instance_Web3.toChecksumAddress(address),
        LoadContractABI(filenameToAbi))
    print('Contract_DiamondProxy = ', Contract_DiamondProxy)


def CreateNewContractObject(name, address, filenameToAbi):
    global ContractsDict

    contractObject = LoadContract(
        Instance_Web3.toChecksumAddress(address),
        LoadContractABI(filenameToAbi))

    ContractsDict[name] = contractObject


def GetContractsDict():
    global ContractsDict
    return ContractsDict


def GetContract_DiamondProxy():
    global Contract_DiamondProxy
    return Contract_DiamondProxy
