from Libraries.nodes import Instance_Web3


class EthereumAccount:
    name = None
    publicAddress = None
    privateKey = None

    # Feel free to add your own wallet encryption/decryption
    # I removed mine to make this code sample simpler

    def __init__(self, _name, _publicAddress, _privateKey):
        self.name = _name
        self.publicAddress = Instance_Web3.toChecksumAddress(_publicAddress)
        self.privateKey = _privateKey
