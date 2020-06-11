from web3 import Web3


def Hash(textToHash):
    hashedText = Web3.sha3(text=textToHash).hex()

    print("")
    print("-----------------------------------------------include this text in your solidity source code:------------------------------------------------")
    print("")
    print('// NOTE: this ds_slot must be the shared if you want to share storage with another contract under the proxy umbrella')
    print('// NOTE: this ds_slot must be unique if you want to NOT share storage with another contract under the proxy umbrella')
    print('// ds_slot = keccak256({0});'.format(textToHash))
    print('assembly {{ ds_slot := {0} }}'.format(hashedText))
    print("")
    print("----------------------------------------------------------------------------------------------------------------------------------------------")
    print("")
    return hashedText
