from web3 import Web3


def GetMethodSignature(methodName, params, doConvertFromBytesToHexString=True):
    textToHash = str(methodName) + "(" + str(params) + ")"
    methodSignature = Web3.sha3(text=textToHash)[0:4]
    # PrintAndLog("methodSignature of type " + str(type(methodSignature)) + " = " + str(methodSignature))
    if doConvertFromBytesToHexString:
        methodSignature = methodSignature.hex()

    return methodSignature


def GetMethodSignature_GivenAbi(methodName, abi):
    # PrintAndLog("found a trade function: " + str(methodName))
    params = ''
    for index, input in enumerate(abi['inputs']):
        if index > 0:
            params += ','

        if input['type'] == 'tuple':
            params += '('
            for index2, tupleComponent in enumerate(input['components']):
                if index2 > 0:
                    params += ','

                params += tupleComponent['type']

            params += ')'

        else:
            params += input['type']

    methodSignature = GetMethodSignature(methodName, params)
    # PrintAndLog("methodSignature = " + str(methodSignature) + ", methodName " + str(methodName) + ", params = " + str(params))
    return methodSignature


def GetFunctionHashListForAllFunctionsInContract(contract, doPrintDebug=False):
    methodSignatureList = []
    for function in contract.all_functions():
        # PrintAndLog_FuncNameHeader("function = " + str(function))
        # PrintAndLog_FuncNameHeader("function.abi = " + str(function.abi))
        # PrintAndLog_FuncNameHeader("function.abi['name'] = " + str(function.abi['name']))

        methodName = function.abi['name']

        methodSignature = GetMethodSignature_GivenAbi(methodName, function.abi)
        if doPrintDebug:
            print("methodSignature = " + str(methodSignature) + " for method " + str(methodName) + " in contract " + str(contract.address))

        methodSignatureList.append(methodSignature.lower())

    return methodSignatureList
