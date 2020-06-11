import configparser
import os
import sys

from past.builtins import raw_input

from Libraries.diamondProxy import DiamondProxy, API_TestProxy_LogicContract_GetFacetAddresses, API_TestProxy_LogicContract_GetFacetFunctionSelectors, \
    API_TestProxy_LogicContract_GetFacetAddress
from Libraries.accounts import EthereumAccount

from Contracts.contracts import Directory_Contracts, CreateNewContractObject, CreateNewProxyContract, GetContract_DiamondProxy, GetContractsDict
from Libraries.core import MergeDictionaries, GetNullAddress, ConvertGweiToWei, IsAddressAValidDeployedContract
from Libraries.signing import GetFunctionHashListForAllFunctionsInContract
from Libraries.utils import ConvertListOfStringsToLowercaseListOfStrings


def Set():
    # Parse the config
    config = configparser.ConfigParser()
    config.read('diamondSetter.config')
    publicAddress = config['ACCOUNT']['publicAddress']
    privateKey = config['ACCOUNT']['privateKey']
    gasPrice_gwei = config['ACCOUNT']['gasPrice_gwei']
    print('gasPrice_gwei = ', gasPrice_gwei)
    gasPrice_wei = ConvertGweiToWei(float(gasPrice_gwei))
    print('gasPrice_wei = ', gasPrice_wei)

    # Verify that the contracts found in the config are actually in the Contracts folder
    address_proxy = config['CONTRACT_PROXY']['address']
    filename_proxy = config['CONTRACT_PROXY']['filename'] + '.json'
    print('address_proxy = ', address_proxy)
    print('filename_proxy = ', filename_proxy)

    CreateNewProxyContract(address_proxy, filename_proxy)

    for name in config['CONTRACTS_LOGIC']:
        filename_abi = name + '.json'
        address = config['CONTRACTS_LOGIC'][name]
        print('found logic contract ' + str(name) + ' whose address is ' + str(address))
        filepath_abi = Directory_Contracts + '/' + filename_abi

        abiExists = os.path.isfile(filepath_abi)
        print('abiExists = ' + str(abiExists))

        # Verify that this address is indeed a real deployed contract
        isValidDeployedContract = IsAddressAValidDeployedContract(address)
        print('isValidDeployedContract = ' + str(isValidDeployedContract))

        if not abiExists:
            raise Exception("Contract named " + str(name) + " at address " + str(
                address) + " was found to missing the abi. Did you put the ABI in the " + str(Directory_Contracts) + " directory?")

        if not isValidDeployedContract:
            raise Exception("Contract named " + str(name) + " at address " + str(
                address) + " was found to not be a deployed contract. Check the address i the config")

        CreateNewContractObject(name, address, filename_abi)

    testAccount = EthereumAccount("accountName", publicAddress, privateKey)

    ninjaProxy = DiamondProxy(testAccount, GetContract_DiamondProxy().address)

    # Hard code a nonce here if you like
    nonce = None

    doRemoveAllFunctionSelectorsForLogicContractsWithin_logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden = True

    # Declare if any logic contracts are eligible to be overwritten
    # Logic contracts NOT listed in here will not be overwritten as a safety measure
    logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden = [
        # nodes.Instance_Web3.toChecksumAddress('PutAddressToOverrideHere'),
        # nodes.Instance_Web3.toChecksumAddress('PutAddressToOverrideHere'),
    ]

    # Consider registering our logic contract with the proxy
    diamondCutDict_updates = {}
    diamondCutDict_removes = {}

    # Before we consider updating, check to see if it's already been registered
    facetAddressList = API_TestProxy_LogicContract_GetFacetAddresses()

    # Declare your logic contracts here that will live under the proxy umbrella
    # logicContractTupleList contains tuples (name, address, contract object)
    logicContractTupleList = []
    for logicContractName in GetContractsDict():
        contractObject = GetContractsDict()[logicContractName]
        logicContractTupleList.append((logicContractName, contractObject.address, contractObject))

    # logicContractTupleList.append(("Ninja_Trade_A", Contract_Logic_A.address, Contract_Logic_A))
    # logicContractTupleList.append(("Properties", Contract_Properties.address, Contract_Properties))

    if doRemoveAllFunctionSelectorsForLogicContractsWithin_logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden:
        for logicContract_toRemove in logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden:
            functionSelectorList = API_TestProxy_LogicContract_GetFacetFunctionSelectors(logicContract_toRemove)
            print('Updating diamondCutDict_removes with functionSelectorList = ' + str(functionSelectorList))

            # Add these functionSelectorList to the diamondCutDict_removes
            # If the null address is already in diamondCutDict_removes
            if GetNullAddress().lower() in diamondCutDict_removes:
                # Combine lists since there's already a list in the value, combine that with our new list of functionSelectorList
                print("Combine lists since there's already a list in the value, combine that with our new list of functionSelectorList")
                print("diamondCutDict_removes[GetNullAddress().lower()] was = " + str(diamondCutDict_removes[GetNullAddress().lower()]))
                print("functionSelectorList is = " + str(functionSelectorList))
                diamondCutDict_removes[GetNullAddress().lower()] += functionSelectorList

            # null address has not yet been added to diamondCutDict_removes
            else:
                print("null address has not yet been added to diamondCutDict_removes")
                diamondCutDict_removes[GetNullAddress().lower()] = functionSelectorList

            print("diamondCutDict_removes[GetNullAddress().lower()] after update is = " + str(
                diamondCutDict_removes[GetNullAddress().lower()]))

        print('diamondCutDict_removes = ' + str(diamondCutDict_removes))

    # Lowercase all the addresses
    logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden = ConvertListOfStringsToLowercaseListOfStrings(
        logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden)

    for logicContractTuple in logicContractTupleList:
        name, logicContractAddress, logicContractObject = logicContractTuple
        print("Checking proxy registration status of the following logic contract: " + str(name) + " " + str(logicContractAddress))
        # Set the key as the logic contract address when setting a new logic contract
        diamondCutDict_updates[logicContractAddress.lower()] = GetFunctionHashListForAllFunctionsInContract(logicContractObject)
        print("Found " + str(len(diamondCutDict_updates[logicContractAddress.lower()])) + " function selectors for this logic contract's ABI. " + str(
            diamondCutDict_updates[logicContractAddress.lower()]))

        functionSelectorList = API_TestProxy_LogicContract_GetFacetFunctionSelectors(logicContractAddress)

        print("Found " + str(len(functionSelectorList)) + " function selectors already registered in the proxy for this logic contract. " + str(
            functionSelectorList))

        # for each function selector, check to see if it's already registered. If it is, remove it from the list in diamondCutDict_updates[logicContractAddress.lower()]
        functionSelectorsToRemoveFromList = []
        for functionSelector in diamondCutDict_updates[logicContractAddress.lower()]:
            functionSelectorLogicAddress = API_TestProxy_LogicContract_GetFacetAddress('0x' + functionSelector)
            doesFunctionSelectorExistInProxy = functionSelectorLogicAddress.lower() != GetNullAddress().lower()
            print("functionSelector = " + str(functionSelector) + ", doesFunctionSelectorExistInProxy = " + str(
                doesFunctionSelectorExistInProxy) + ", functionSelectorLogicAddress = " + str(functionSelectorLogicAddress))
            if doesFunctionSelectorExistInProxy:
                if functionSelectorLogicAddress.lower() == logicContractAddress.lower():
                    print("Remove the functionSelector from the diamondCutDict_updates's list because it's already set properly")
                    functionSelectorsToRemoveFromList.append(functionSelector)
                else:
                    # We have been instructed to overwrite a logic address' function selector.
                    # Check to see whether or not we have been given permission
                    if functionSelectorLogicAddress.lower() in logicContractList_whoseFunctionSelectorsAreEligibleToBeOverridden:
                        print("We have been given permission to overwrite function selectors in logic contract " + str(functionSelectorLogicAddress))
                    else:
                        print("We have NOT been given permission to overwrite function selectors in logic contract: name = " + str(
                            name) + ", logicContractAddress = " + str(logicContractAddress) + " and functionSelector = " + str(functionSelector))
                        raise Exception("I caught myself trying to overwrite a function! "
                                        "Do I have the same exact function in two different logic contracts? This is bad, NEVER do this!")

            else:
                print("The function selector is not registered in the proxy, so we are free to add it at will")
                pass

        print("Removing " + str(len(functionSelectorsToRemoveFromList)) + " function selectors from " + str(name) + " because they are already registered")
        for functionSelector in functionSelectorsToRemoveFromList:
            diamondCutDict_updates[logicContractAddress.lower()].remove(functionSelector)

        print("diamondCutDict_updates[logicContractAddress.lower()] after removing already registered function selectors, = " + str(
            diamondCutDict_updates[logicContractAddress.lower()]))

        if len(diamondCutDict_updates[logicContractAddress.lower()]) <= 0:
            print("Removing " + str(name) + " " + str(logicContractAddress) + " from diamondCutDict_updates all together because it's already up to date")
            del diamondCutDict_updates[logicContractAddress.lower()]

        if logicContractAddress.lower() in diamondCutDict_updates and len(diamondCutDict_updates[logicContractAddress.lower()]) > 0:
            print("Adding " + str(len(diamondCutDict_updates[logicContractAddress.lower()])) + " function selectors for " + str(
                name) + " " + str(logicContractAddress) + " to diamondCutDict_updates. diamondCutDict_updates = " + str(diamondCutDict_updates))
        else:
            print("NOT updating function selectors for " + str(name) + " " + str(
                logicContractAddress) + " to diamondCutDict_updates because they would override. diamondCutDict_updates = " + str(diamondCutDict_updates))

    # Merge diamondCutDict_updates with diamondCutDict_removes
    print("diamondCutDict_removes = " + str(diamondCutDict_removes))
    print("diamondCutDict_updates = " + str(diamondCutDict_updates))
    diamondCutDict_merged = MergeDictionaries(diamondCutDict_updates, diamondCutDict_removes)
    print("Merged diamondCutDict_merged and diamondCutDict_merged")
    print("diamondCutDict_merged = " + str(diamondCutDict_merged))

    if len(diamondCutDict_merged) <= 0:
        print("Not calling API_DiamondCut because diamondCutDict_merged was empty. diamondCutDict_merged = " + str(diamondCutDict_merged))

    else:
        userInput = raw_input("Do you want to execute this API_DiamondCut?  y/n:  ")

        if userInput.lower() == 'y':
            print("Calling API_DiamondCut")
            ninjaProxy.API_DiamondCut(diamondCutDict_merged, gasPrice_wei, nonce)
        else:
            print("Not calling API_DiamondCut")
