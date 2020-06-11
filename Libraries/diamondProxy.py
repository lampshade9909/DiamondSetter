import random
import string
import json
from web3 import Web3
from eth_abi import encode_single

from Libraries.utils import ConvertListOfStringsToLowercaseListOfStrings
from Libraries.transactions import API_SendEther_ToContract, TransactionType

from Libraries.core import GetAddressFromDataProperty, Headers, RequestTimeout_seconds, API_EstimateGas, GetNullAddress, SendRequestToAllNodes, \
    SplitStringIntoChunks, LengthOfDataProperty, LengthOfPublicAddress_Excludes0x
from Libraries.nodes import Instance_Web3


class DiamondProxy:
    operatorAccount = None
    proxyAddress = None

    def __init__(self, _operatorAccount, _proxyAddress):
        self.operatorAccount = _operatorAccount
        self.proxyAddress = _proxyAddress

    def API_DiamondCut(self, diamondCutDict, gasPrice=None, nonce=None):
        return API_DiamondCut_GivenDiamondCutDict(self.operatorAccount.publicAddress, self.operatorAccount.privateKey,
                                                  self.proxyAddress, diamondCutDict, gasPrice, nonce)


def API_DiamondCut_GivenDiamondCutDict(fromAddress, fromPrivateKey, proxyAddress, diamondCutDict, gasPrice, nonce=None):
    print("diamondCutDict = " + str(diamondCutDict))

    if len(diamondCutDict) <= 0:
        raise Exception("There aren't any diamonds in here. diamondCutDict = " + str(diamondCutDict))

    # diamondCutDict is keyed by the facetAddress
    # diamondCutDict value is a list of the facet's function hash selectors
    # for example, for ['0x998497ffc64240d6a70c38e544521d09dcd2329399f5f52e01ffc9a7cdffacc6']
    # { '0x998497ffc64240d6a70c38e544521d09dcd23293': ['0x99f5f52e', '0x01ffc9a7', '0xcdffacc6'] }
    # This means:
    #   the facetAddress is 0x998497ffc64240d6a70c38e544521d09dcd23293
    #   the function hashes are ['0x99f5f52e', '0x01ffc9a7', '0xcdffacc6']

    # Construct the diamondCutList from the diamondCutDict
    diamondCutList = []
    for facetAddress in diamondCutDict:
        selectorList = diamondCutDict[facetAddress]
        if len(selectorList) <= 0:
            print("There aren't any selectors in here! selectorList = " + str(
                selectorList) + ", facetAddress = " + str(facetAddress) + ". Not including it in the diamondCutList")
            continue

        diamondCutString = CreateDiamondCutString(facetAddress, selectorList)
        print("diamondCutString = " + str(diamondCutString))

        # Order is important here.  Currently, I want the REMOVES to be first and the updates to be last
        # So if I'm making 4 updates, order doesn't matter.
        # But if i'm making 2 removes and 10 updates, the removes must come first, and the updates must come last
        # This is to prevent myself from updating something and then removing it immediately after
        # If this is a remove
        if facetAddress.lower() == GetNullAddress().lower():
            # Insert at beginning of list so we always do removes first
            diamondCutList.insert(0, Web3.toBytes(hexstr=str(diamondCutString)))
        else:
            # Append updates to end of list so we always update after we remove
            diamondCutList.append(Web3.toBytes(hexstr=str(diamondCutString)))

    print("diamondCutList = " + str(diamondCutList))
    return API_DiamondCut_GivenDiamondCutList(fromAddress, fromPrivateKey, proxyAddress, diamondCutList, gasPrice, nonce)


def API_DiamondCut_GivenDiamondCutList(fromAddress, fromPrivateKey, proxyAddress, diamondCutList, gasPrice, nonce=None):
    print("proxyAddress = " + str(proxyAddress))

    # function diamondCut(
    #         bytes[] memory _diamondCut
    #         ) public override

    if len(diamondCutList) <= 0:
        raise Exception("diamondCutList was empty! Was this intentional?")

    print("diamondCutList = " + str(diamondCutList))
    params = 'bytes[]'
    method_signature = Web3.sha3(text=f"diamondCut({params})")[0:4]
    method_parameters = encode_single(f"({params})", [diamondCutList])
    data_hex = '0x' + (method_signature + method_parameters).hex()

    print("method_signature = " + str(method_signature))
    print("method_parameters = " + str(method_parameters))
    print("data_hex = " + str(data_hex))

    toAddress = Instance_Web3.toChecksumAddress(proxyAddress)
    print("toAddress = " + str(toAddress))
    # API_EthCall(toAddress, fromAddress, data_hex)
    estimatedGas = API_EstimateGas(toAddress, fromAddress, data_hex)
    # estimatedGas = 510978
    print("estimatedGas = " + str(estimatedGas))

    transactionId = API_SendEther_ToContract(Instance_Web3.toChecksumAddress(fromAddress), fromPrivateKey,
                                             toAddress, 0, estimatedGas, gasPrice, data_hex, TransactionType.other, nonce)
    # Trash the fromPrivateKey in memory
    fromPrivateKey = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(101))

    return transactionId


def CreateDiamondCutString(facetAddress, selectorList):
    # diamondCutDict is keyed by the facetAddress
    # diamondCutDict value is a list of the facet's function hash selectors
    # for example, for ['0x998497ffc64240d6a70c38e544521d09dcd2329399f5f52e01ffc9a7cdffacc6']
    # { '0x998497ffc64240d6a70c38e544521d09dcd23293': ['0x99f5f52e', '0x01ffc9a7', '0xcdffacc6'] }
    # This means:
    #   the facetAddress is 0x998497ffc64240d6a70c38e544521d09dcd23293
    #   the function hashes are ['0x99f5f52e', '0x01ffc9a7', '0xcdffacc6']

    returnString = ''
    returnString += facetAddress
    for selector in selectorList:
        returnString += selector.replace("0x", "")

    return returnString


def API_TestProxy_LogicContract_GetFacetAddresses():
    import Contracts.contracts

    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "data": Contracts.contracts.Contract_DiamondLoupe.encodeABI('facetAddresses', kwargs={}),
                "to": Instance_Web3.toChecksumAddress(Contracts.contracts.Contract_DiamondProxy.address),
            },
        ]
    }
    # print("payload = " + str(payload))
    response = SendRequestToAllNodes(payload, Headers, RequestTimeout_seconds)
    if response.ok:
        responseData = response.content
        jData = json.loads(responseData)
        # print("jData = " + str(jData))
        result = jData['result'].replace("0x", "")
        splitArray = SplitStringIntoChunks(result, LengthOfDataProperty)
        # print("splitArray = " + str(splitArray))
        # We don't need the first two items
        splitArray.pop(0)
        splitArray.pop(0)
        # print("splitArray = " + str(splitArray))

        # Make one giant string out of what's left
        giantString = ''
        for item in splitArray:
            giantString += item.lower()

        # print("giantString = " + str(giantString))

        # Make an array of address length strings out of the giant string
        facetAddressList = SplitStringIntoChunks(giantString, LengthOfPublicAddress_Excludes0x)
        print("facetAddressList = " + str(facetAddressList))
        # Make sure every string is lowercase
        facetAddressList = ConvertListOfStringsToLowercaseListOfStrings(facetAddressList)
        return facetAddressList

    else:
        # If response code is not ok (200), print the resulting http error code with description
        print("response was not ok response = " + str(response))
        response.raise_for_status()


def API_TestProxy_LogicContract_GetFacetFunctionSelectors(facetAddress):
    import Contracts.contracts

    kwargs = {
        '_facet': facetAddress,
    }

    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "data": Contracts.contracts.Contract_DiamondLoupe.encodeABI('facetFunctionSelectors', kwargs=kwargs),
                "to": Instance_Web3.toChecksumAddress(Contracts.contracts.Contract_DiamondProxy.address),
            },
        ]
    }
    # print("payload = " + str(payload))
    response = SendRequestToAllNodes(payload, Headers, RequestTimeout_seconds)
    if response.ok:
        responseData = response.content
        jData = json.loads(responseData)
        # print("jData = " + str(jData))
        result = jData['result'].replace("0x", "")
        splitArray = SplitStringIntoChunks(result, LengthOfDataProperty)
        # print("splitArray = " + str(splitArray))

        # We don't need the first two items
        splitArray.pop(0)
        splitArray.pop(0)
        # print("splitArray = " + str(splitArray))

        # Make one giant string out of what's left
        giantString = ''
        for item in splitArray:
            giantString += item.lower()

        # print("giantString = " + str(giantString))

        # Make an array of 8 character strings out of the giant string
        functionSelectorList = SplitStringIntoChunks(giantString, 8)
        print("functionSelectorList = " + str(functionSelectorList))
        # Make sure every string is lowercase
        functionSelectorList = ConvertListOfStringsToLowercaseListOfStrings(functionSelectorList)
        print("functionSelectorList after lowercasing = " + str(functionSelectorList))

        # HACK I must remove all 0x00000000 function selectors because they were just most likely padding and shouldn't be a function selector
        # But in theory a function could pan out to have a hash of 0x00000000 right???
        newList = []
        for functionSelector in functionSelectorList:
            if functionSelector.lower() != "00000000":
                newList.append(functionSelector)

        functionSelectorList = newList
        print("functionSelectorList after removing 0's = " + str(functionSelectorList))
        return functionSelectorList

    else:
        # If response code is not ok (200), print the resulting http error code with description
        print("response was not ok response = " + str(response))
        response.raise_for_status()


def API_TestProxy_LogicContract_GetFacetAddress(functionSelector):
    import Contracts.contracts

    kwargs = {
        '_functionSelector': Web3.toBytes(hexstr=str(functionSelector)),
    }

    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "data": Contracts.contracts.Contract_DiamondLoupe.encodeABI('facetAddress', kwargs=kwargs),
                "to": Instance_Web3.toChecksumAddress(Contracts.contracts.Contract_DiamondProxy.address),
            },
        ]
    }
    # print("payload = " + str(payload))
    response = SendRequestToAllNodes(payload, Headers, RequestTimeout_seconds)
    if response.ok:
        responseData = response.content
        jData = json.loads(responseData)
        # print("jData = " + str(jData))
        return GetAddressFromDataProperty(jData['result'])

    else:
        # If response code is not ok (200), print the resulting http error code with description
        print("response was not ok response = " + str(response))
        response.raise_for_status()
