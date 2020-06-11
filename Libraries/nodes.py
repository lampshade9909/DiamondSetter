import configparser
from enum import Enum
from web3 import Web3, HTTPProvider

config = configparser.ConfigParser()
config.read('diamondSetter.config')
configSections = config.sections()
nodeUrl = config['NODE']['url']
print('nodeUrl = ', nodeUrl)


class URL_RemoteNode(Enum):
    myNode = nodeUrl


RemoteNodeList = []

RemoteNodeList.append(URL_RemoteNode.myNode)

Instance_Web3 = Web3(HTTPProvider(URL_RemoteNode.myNode.value))
