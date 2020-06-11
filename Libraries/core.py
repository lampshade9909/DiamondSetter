import copy
import json
import threading
import time
import traceback
from random import randint
from threading import Lock
import requests
import rlp
from ethereum import transactions
from web3 import Web3

RequestTimeout_seconds = 6
LengthOfDataProperty = 64
LengthOfPrivateKey = 64
LengthOfPublicAddress_Including0x = 42
LengthOfPublicAddress_Excludes0x = 40
LengthOfTransactionHash_Including0x = 66
LengthOfTransactionHash_Excludes0x = 64

Headers = {'content-type': 'application/json'}

RequestTimeout_seconds = 5


def ConvertIntToHex(number_int):
    return "%x" % int(number_int)


def MergeDictionaries(x, y):
    z = x.copy()  # start with x's keys and values
    z.update(y)  # modifies z with y's keys and values & returns None
    return z


def SendRequestToAllNodes(payload, headers, requestTimeout_seconds, resultHandlerDelegate=None,
                          doSetBlockNumber_BasedOnLatestBlockNumber_int=True,
                          requiredToWaitForAllNodesResponsesBeforeYouConsiderResults=False,
                          payloadIsBatched=False, doRejectBatchedPayloadIfAnyOneHasError=True, specifiedBlockNumber_int=None):
    from Libraries.nodes import RemoteNodeList

    return SendRequestToSpecifiedNodes(RemoteNodeList, payload, headers, requestTimeout_seconds, resultHandlerDelegate,
                                       doSetBlockNumber_BasedOnLatestBlockNumber_int,
                                       requiredToWaitForAllNodesResponsesBeforeYouConsiderResults,
                                       payloadIsBatched, doRejectBatchedPayloadIfAnyOneHasError, specifiedBlockNumber_int)


def SendRequestToSpecifiedNodes(remoteNodeList_toUse, payload, headers, requestTimeout_seconds, resultHandlerDelegate=None,
                                doSetBlockNumber_BasedOnLatestBlockNumber_int=True,
                                requiredToWaitForAllNodesResponsesBeforeYouConsiderResults=False,
                                payloadIsBatched=False, doRejectBatchedPayloadIfAnyOneHasError=True, specifiedBlockNumber_int=None):
    global LatestBlockNumber_int

    if doSetBlockNumber_BasedOnLatestBlockNumber_int and specifiedBlockNumber_int:
        print("Setting both of these is not valid. Only one can be set: doSetBlockNumber_BasedOnLatestBlockNumber_int "
              "and specifiedBlockNumber_int. Overriding doSetBlockNumber_BasedOnLatestBlockNumber_int to False.")
        doSetBlockNumber_BasedOnLatestBlockNumber_int = False

    numOfBatchedRequests = 0
    if payloadIsBatched:
        numOfBatchedRequests = len(payload)

    # print("SendRequestToSpecifiedNodes: numOfBatchedRequests = " + str(numOfBatchedRequests))
    threads = []
    resultDict = {}
    lock_resultDict = Lock()
    numOfExpectedResults = len(remoteNodeList_toUse)
    for remoteNode in remoteNodeList_toUse:
        # Reverse the order, instead of going for 0, 1, 2, 3... Go 3, 2, 1, 0

        resultKey = str(remoteNode.name)

        blockNumber_toUse = None

        # Execute the call with this blockNumber_toUse
        # print("SendRequestToSpecifiedNodes: node = " + str(remoteNode.name) + ", payload = " + str(payload))
        t = threading.Thread(target=SubmitRequest, args=(Get_RemoteEthereumNodeToUse(remoteNode), payload, payloadIsBatched, headers, requestTimeout_seconds,
                                                         blockNumber_toUse, resultDict, resultKey, lock_resultDict,))
        t.start()
        threads.append(t)

    # TODO, Instead of doing a .join and waiting for all to finish.
    # Some may timeout, so I want to proceed as soon as at least one valid response comes in.
    # Don't wait for many valid responses or else i'll lag everything
    # for thread in threads:
    #     thread.join()

    elapsedTime_ms = 0
    timeout_ms = requestTimeout_seconds * 1000
    # Keep this low, as long as we don't have a million print/log statements.  The more print/log statements the more it will slow everything down
    sleepTime_ms = 5
    sleepTime_s = sleepTime_ms / 1000
    foundValidRecentResponse = False
    currentResultDictLength = 0
    previousResultDictLength = 0
    while elapsedTime_ms < timeout_ms:
        # Create a copy so it's threadsafe, we need to do this because new data could come in at any moment since i'm making so many requests
        lock_resultDict.acquire()
        try:
            resultDict_copy = copy.deepcopy(resultDict)

        finally:
            lock_resultDict.release()

        currentResultDictLength = len(resultDict_copy)
        # print("resultDict_copy, waiting for responses. We have " + str(currentResultDictLength) + " of " + str(numOfExpectedResults) + " = " + str(resultDict_copy))

        if currentResultDictLength == numOfExpectedResults:
            # print("Received all responses, breaking from loop")
            break

        # Consider breaking if i've found a result that satisfies me.
        # Tricky thing is, some calls will want to wait for all results to come in before it analyzes results and some calls are willing to go with the first good looking result.
        # So check the requiredToWaitForAllNodesResponsesBeforeYouConsiderResults flag
        elif not requiredToWaitForAllNodesResponsesBeforeYouConsiderResults:
            if currentResultDictLength > 0:
                # if not resultHandlerDelegate and currentResultDictLength > 0:
                # print("currentResultDictLength = " + str(currentResultDictLength) + ", previousResultDictLength = " + str(previousResultDictLength))
                # Only call DetermineMostRecentValidResponseFromResultDict when we have new data
                if currentResultDictLength == previousResultDictLength:
                    # print("Not calling DetermineMostRecentValidResponseFromResultDict because we don't have any new data since last time through the loop")
                    pass
                else:
                    # Set the previous now that we have new data
                    previousResultDictLength = currentResultDictLength
                    # print("Calling DetermineMostRecentValidResponseFromResultDict because we have have new data since last time through the loop")
                    # print("We haven't yet received all responses but let's check to see if the responses we received are valid enough")
                    # Call DetermineMostRecentValidResponseFromResultDict but do not yet raise an exception if it's not valid because we're still waiting for some API calls to return
                    if DetermineMostRecentValidResponseFromResultDict(resultDict_copy, remoteNodeList_toUse,
                                                                      doSetBlockNumber_BasedOnLatestBlockNumber_int,
                                                                      payloadIsBatched, numOfBatchedRequests, doRejectBatchedPayloadIfAnyOneHasError,
                                                                      False):
                        # print("We found a valid recent response! Breaking despite not yet receiving all responses")
                        foundValidRecentResponse = True
                        break

        time.sleep(sleepTime_s)
        elapsedTime_ms += sleepTime_ms

    # if not foundValidRecentResponse and currentResultDictLength != numOfExpectedResults:
    #     print("Timed out before we received all responses")

    # Create a copy so it's threadsafe, we need to do this because new data could come in at any moment since i'm making so many requests
    lock_resultDict.acquire()
    try:
        resultDict_copy = copy.deepcopy(resultDict)

    finally:
        lock_resultDict.release()

    firstNcharacters = 500

    # This print statement will show me which nodes got success responses and which got timeouts or known errors we're catching
    if not payloadIsBatched:
        print("SendRequestToSpecifiedNodes: resultDict for " + str(payload['method']) + " = " + str(resultDict_copy))

        # # This below loop with print statements will show me the content in each response for each node
        # for resultKey in resultDict_copy:
        #     if hasattr(resultDict_copy[resultKey], 'content'):
        #         print("SendRequestToSpecifiedNodes: resultDict w/ content = " + str(resultDict_copy[resultKey].content)[0:firstNcharacters] + "...")
        #     else:
        #         print("SendRequestToSpecifiedNodes: resultDict w/ string value = " + str(resultDict_copy[resultKey])[0:firstNcharacters] + "...")

    else:
        listOfMethods = []
        for batchedPayload in payload:
            listOfMethods.append(batchedPayload['method'])

        print("SendRequestToSpecifiedNodes: resultDict for " + str(listOfMethods) + " = " + str(resultDict_copy))

        # # This below loop with print statements will show me the content in each response for each node
        # for resultKey in resultDict_copy:
        #     if hasattr(resultDict_copy[resultKey], 'content'):
        #         print("SendRequestToSpecifiedNodes: resultDict w/ content = " + str(resultDict_copy[resultKey].content)[0:firstNcharacters] + "...")
        #     else:
        #         print("SendRequestToSpecifiedNodes: resultDict w/ string value = " + str(resultDict_copy[resultKey])[0:firstNcharacters] + "...")

    if resultHandlerDelegate:
        # print("SendRequestToSpecifiedNodes: calling resultHandlerDelegate")
        return resultHandlerDelegate(resultDict_copy)

    else:
        # Create a copy so it's threadsafe, we need to do this because new data could come in at any moment since i'm making so many requests
        lock_resultDict.acquire()
        try:
            resultDict_copy = copy.deepcopy(resultDict)

        finally:
            lock_resultDict.release()

        # print("SendRequestToSpecifiedNodes: returning DetermineMostRecentValidResponseFromResultDict")
        return DetermineMostRecentValidResponseFromResultDict(resultDict_copy, remoteNodeList_toUse,
                                                              doSetBlockNumber_BasedOnLatestBlockNumber_int,
                                                              payloadIsBatched, numOfBatchedRequests, doRejectBatchedPayloadIfAnyOneHasError)


def DetermineMostRecentValidResponseFromResultDict(resultDict, remoteNodeList,
                                                   doSetBlockNumber_BasedOnLatestBlockNumber_int,
                                                   payloadIsBatched, numOfBatchedRequests, doRejectBatchedPayloadIfAnyOneHasError,
                                                   doRaiseExceptionIfNotValid=True):
    # So here the resultDict contains a bunch of results.  Some are valid and some are not.  Of the valid ones, some are for different block numbers.
    # Find the most recent valid one
    doPrintDebug = False

    # If we have many batched responses per node call
    if payloadIsBatched:
        mostRecentValidResponse = None
        resultKeyForMostRecentValidResponse = None

        for resultKey in resultDict:
            resultString = None
            if not hasattr(resultDict[resultKey], 'content'):
                resultString = "ERROR, Could not parse response into JSON"
            else:
                responseData = resultDict[resultKey].content
                jData = json.loads(responseData)
                # Count how many times a response failed
                count_failed = 0
                # Increment the fails for each time a response didn't come in per a request
                numOfBatchedResponses = len(jData)
                count_failed += numOfBatchedRequests - numOfBatchedResponses

                for batchedJData in jData:
                    if doPrintDebug:
                        print("DetermineMostRecentValidResponseFromResultDict: Found result batchedJData: " + str(batchedJData))

                    if 'error' in batchedJData:
                        resultString = str(batchedJData['error'])
                        count_failed += 1

                    elif 'result' in batchedJData and batchedJData['result'] and str(batchedJData['result']).lower() != "null" and str(
                            batchedJData['result']).lower() != "0x":
                        resultString = str(batchedJData['result'])

                    else:
                        resultString = "ERROR, Could not find result in response"
                        count_failed += 1

                # Once it's all done iterating over the batched responses, if count_failed is still zero
                if count_failed == 0 or not doRejectBatchedPayloadIfAnyOneHasError:
                    # Then assume we have good data
                    mostRecentValidResponse = resultDict[resultKey]
                    resultKeyForMostRecentValidResponse = resultKey

            if doPrintDebug:
                print("DetermineMostRecentValidResponseFromResultDict: numOfBatchedRequests = " + str(numOfBatchedRequests) + ", numOfBatchedResponses = " + str(
                    numOfBatchedResponses) + ", count_failed = " + str(count_failed) + " after iterating over all batched responses")
                print("DetermineMostRecentValidResponseFromResultDict: Found result: " + str(resultString))

        if mostRecentValidResponse:
            return mostRecentValidResponse
        else:
            # I cannot return anything since this is not a valid response
            return None

    # Else we have only one response to deal with per node call
    else:
        mostRecentValidResponse = None
        highestBlockNumber = 0
        resultKeyForMostRecentValidResponse = None

        if doPrintDebug:
            print("DetermineMostRecentValidResponseFromResultDict: resultDict = " + str(resultDict))
            print("DetermineMostRecentValidResponseFromResultDict: remoteNodeList = " + str(remoteNodeList))

        for resultKey in resultDict:
            resultString = None
            if not hasattr(resultDict[resultKey], 'content'):
                resultString = "ERROR, Could not parse response into JSON"
            else:
                responseData = resultDict[resultKey].content
                jData = json.loads(responseData)
                if doPrintDebug:
                    print("DetermineMostRecentValidResponseFromResultDict: Found result jData: " + str(jData))

                if 'error' in jData:
                    resultString = str(jData['error'])

                elif 'result' in jData and jData['result'] and str(jData['result']).lower() != "null" and str(jData['result']).lower() != "0x":
                    resultString = str(jData['result'])

                    # If we're making the call based on a specific block number then I should verify the block number before I say it's valid
                    if doSetBlockNumber_BasedOnLatestBlockNumber_int:
                        if doPrintDebug:
                            print("DetermineMostRecentValidResponseFromResultDict: Analyzing mostRecentValidResponse = " + str(
                                mostRecentValidResponse) + ", highestBlockNumber = " + str(highestBlockNumber) + ", resultKey = " + str(resultKey))
                        # Verify the block number before I assume it's valid
                        if not mostRecentValidResponse:
                            mostRecentValidResponse = resultDict[resultKey]
                            resultKeyForMostRecentValidResponse = resultKey

                    # Else we're making the call based on the 'latest' instead of a specific block number
                    else:
                        if doPrintDebug:
                            print("DetermineMostRecentValidResponseFromResultDict: Analyzing mostRecentValidResponse = " + str(
                                mostRecentValidResponse) + ", highestBlockNumber = " + str(highestBlockNumber) + ", resultKey = " + str(resultKey))
                        mostRecentValidResponse = resultDict[resultKey]
                        highestBlockNumber = None
                        resultKeyForMostRecentValidResponse = resultKey

                else:
                    resultString = "ERROR, Could not find result in response"

            if doPrintDebug:
                print("DetermineMostRecentValidResponseFromResultDict: Found result: " + str(resultString))

        if mostRecentValidResponse:
            # We're making the call based on the 'latest' instead of a specific block number
            return mostRecentValidResponse

        else:
            if doRaiseExceptionIfNotValid:
                message = "DetermineMostRecentValidResponseFromResultDict: Did not find a valid response in SendRequestToSpecifiedNodes out of " + str(
                    len(remoteNodeList)) + " nodes"

                raise Exception(message)


def RemovePropertyFromPayloadParams(property, payload):
    if property in payload['params']:
        payload['params'].remove(property)


def SubmitRequest(url, payload, payloadIsBatched, headers, requestTimeout_seconds, blockNumber_toUse, resultDict, resultKey, lock_resultDict=None):
    # Make a copy of the payload object and modify the copy
    payload_copyToUse = copy.deepcopy(payload)

    if not payloadIsBatched:
        # Set the id if it's not already set
        if 'id' not in payload_copyToUse:
            # Set the id to the payload_copyToUse
            payload_copyToUse['id'] = (randint(0, 999999999999999))

        # Clear these block number properties.  Make sure block properties like 'latest', 'pending', etc are not in the params
        RemovePropertyFromPayloadParams('latest', payload_copyToUse)
        RemovePropertyFromPayloadParams('pending', payload_copyToUse)
        RemovePropertyFromPayloadParams('earliest', payload_copyToUse)
    else:
        for batchedPayload in payload_copyToUse:
            # print("SubmitRequest: batchedPayload before setting id = " + str(batchedPayload))
            # Set the id if it's not already set
            if 'id' not in batchedPayload:
                # Set the id to the payload_copyToUse
                batchedPayload['id'] = (randint(0, 999999999999999))

            # print("SubmitRequest: batchedPayload after setting id = " + str(batchedPayload))

            # Clear these block number properties.  Make sure block properties like 'latest', 'pending', etc are not in the params
            RemovePropertyFromPayloadParams('latest', batchedPayload)
            RemovePropertyFromPayloadParams('pending', batchedPayload)
            RemovePropertyFromPayloadParams('earliest', batchedPayload)

    blockNumberParamIsRequired = True
    if not payloadIsBatched:
        method = payload_copyToUse['method']
        if not RpcMethodRequiresBlockNumberSpecification(method):
            # print("SubmitRequest: not specifying block number for this call because it will throw an error if we do")
            blockNumberParamIsRequired = False
    else:
        for batchedPayload in payload_copyToUse:
            method = batchedPayload['method']
            # If anyone one of these methods in this batched call behave this way, treat the entire thing this way
            if not RpcMethodRequiresBlockNumberSpecification(method):
                blockNumberParamIsRequired = False
                break

    if blockNumberParamIsRequired:
        if not blockNumber_toUse:
            if not payloadIsBatched:
                # We're using only the latest
                payload_copyToUse['params'].append('latest')
            else:
                for batchedPayload in payload_copyToUse:
                    # We're using only the latest
                    batchedPayload['params'].append('latest')
        else:
            if not payloadIsBatched:
                # Append the block number to the payload_copyToUse
                # print("Before payload_copyToUse = " + str(payload_copyToUse))
                payload_copyToUse['params'].append(blockNumber_toUse)
                # print("After payload_copyToUse = " + str(payload_copyToUse))
            else:
                for batchedPayload in payload_copyToUse:
                    # Append the block number to the batchedPayload
                    # print("Before batchedPayload = " + str(batchedPayload))
                    batchedPayload['params'].append(blockNumber_toUse)
                    # print("After batchedPayload = " + str(batchedPayload))

    try:
        # print("SubmitRequest: to " + str(url) + " with payload " + str(payload_copyToUse))
        # datetimeBefore = datetime.datetime.now()
        response = requests.post(url, data=json.dumps(payload_copyToUse), headers=headers, timeout=requestTimeout_seconds)
        # duration_s = (datetime.datetime.now() - datetimeBefore).total_seconds()
        # print("SubmitRequest: to " + str(url) + " duration_s = " + str(duration_s))

    except Exception as ex:
        print("exception (unknown) in SubmitRequest: ex = " + str(type(ex)) + ", stacktrace = " + str(traceback.format_exc()))
        # # Do not print the stacktrace to logs or i'll get spammed and performance will suffer
        response = "wtf"
        pass

    # response = requests.post(url, data=json.dumps(payload_copyToUse), headers=headers, timeout=requestTimeout_seconds)
    # print("SubmitRequest: response = " + str(response))
    # print("SubmitRequest: response.content = " + str(response.content) + ", this was for url = " + str(url))

    # if there's no lock, just update the resultDict
    if not lock_resultDict:
        resultDict[resultKey] = response
    # Else we have a lock, so let's update the resultDict in a threadsafe way
    else:
        lock_resultDict.acquire()
        try:
            resultDict[resultKey] = response

        finally:
            lock_resultDict.release()


def RpcMethodRequiresBlockNumberSpecification(method):
    # Some RPC calls requires a block number specification (aka no block number, no "latest", etc)
    if method == 'eth_blockNumber' or \
            method == 'eth_estimateGas' or \
            method == 'eth_getBlockTransactionCountByHash' or \
            method == 'eth_sendTransaction' or \
            method == 'eth_sendrawtransaction' or \
            method == 'eth_estimategas' or \
            method == 'eth_getBlockByHash' or \
            method == 'eth_getTransactionByHash' or \
            method == 'eth_getTransactionByBlockHashAndIndex' or \
            method == 'eth_getTransactionReceipt' or \
            method == 'eth_pendingTransactions' or \
            method == 'eth_getBlockByNumber' or \
            method == 'eth_pendingTransactions' or \
            method == 'eth_gasPrice' or \
            method == 'eth_getLogs' or \
            method == 'eth_sendRawTransaction':
        return False
    else:
        return True


def Get_RemoteEthereumNodeToUse(url_RemoteNode):
    return url_RemoteNode.value


def API_GetTransactionCount(address):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [
            address,
        ]
    }
    # print("payload = " + str(payload))
    response = SendRequestToAllNodes(payload, Headers, RequestTimeout_seconds,
                                     ResultHandlerDelegate_DetermineHighestResult_int,
                                     True, True)
    if response.ok:
        responseData = response.content
        jData = json.loads(responseData)
        # print("API_GetTransactionCount jData = " + str(jData))
        transactionCount = ConvertHexToInt(jData['result'])
        return transactionCount

    else:
        # If response code is not ok (200), print the resulting http error code with description
        response.raise_for_status()


def ResultHandlerDelegate_DetermineHighestResult_int(resultDict):
    highestResult = 0

    # This function is great because it's going to look at the resultDict which contains many responses and iterate over them and look for the response with the highest result
    # This works well for the getting the latest block number as well as getting the latest nonce.  In both cases we want the highest value

    responseOf_highestResult = None
    for resultKey in resultDict:
        # PrintAndLog_FuncNameHeader("resultKey = " + str(resultKey) + ": resultDict[resultKey] = " + str(resultDict[resultKey]))
        if hasattr(resultDict[resultKey], 'content'):
            responseData = resultDict[resultKey].content
            jData = json.loads(responseData)
            # PrintAndLog_FuncNameHeader("jData = " + str(jData))
            # If the result is valid
            if 'result' in jData and jData['result'] and str(jData['result']).lower() != "null" and str(jData['result']).lower() != "none":
                result = ConvertHexToInt(jData['result'])
                # PrintAndLog_FuncNameHeader("jData['result'] = " + str(jData['result']) + ", " + str(result) + " " + str(resultKey))
                if result > highestResult:
                    # PrintAndLog_FuncNameHeader("found a new highest result " + str(result) + ", " + str(resultKey))
                    highestResult = result
                    responseOf_highestResult = resultDict[resultKey]
                # else:
                #     PrintAndLog_FuncNameHeader("found a result " + str(
                #         result) + ", but it didn't exceed our current highest of " + str(highestResult) + " " + str(resultKey))

    return responseOf_highestResult


def API_SendRawTransaction_ToManyRemoteNodes(transactionData):
    from Libraries.nodes import RemoteNodeList

    threads = []
    resultsDict = {}

    # Send to all standard RPC nodes
    for remoteNode in RemoteNodeList:
        key = str(remoteNode.name)
        t = threading.Thread(target=API_PostSendRawTransaction_StandardRPC, args=(transactionData, Get_RemoteEthereumNodeToUse(remoteNode), resultsDict, key))
        threads.append(t)
        t.start()

    for thread in threads:
        thread.join()

    print("resultsDict = " + str(resultsDict))
    # print("resultsDict.values() = " + str(resultsDict.values()))

    numOfTransactionIdsInResultsDict = 0
    for key, txId in list(resultsDict.items()):
        if IsStringATransactionId(txId):
            numOfTransactionIdsInResultsDict += 1

    print("numOfTransactionIdsInResultsDict = " + str(numOfTransactionIdsInResultsDict))

    # If all of these responses are the same, then we can just reference the first one
    if AllListItemsAreTheSame(list(resultsDict.values())):
        print("All items are the same")
        txId = list(resultsDict.values())[0]

        if IsStringATransactionId(txId):
            print("Using txId = " + txId)
            return txId, None
        else:
            message = "API_PostSendRawTransaction_ToManyRemoteNodes invalid txId (A) " + str(txId)
            print(message)

    # All responses are not the same
    else:
        print("All items are NOT the same")
        for key, txId in list(resultsDict.items()):
            if IsStringATransactionId(txId):
                print("Using txId = " + txId)
                return txId, None
            else:
                message = "API_PostSendRawTransaction_ToManyRemoteNodes invalid txId (B) " + str(txId)
                print(message)

    return None, None


def API_PostSendRawTransaction_StandardRPC(transactionData, url, result, key):
    shortName = url[0:20]
    result[key] = None
    try:
        payload = {
            "id": randint(0, 99999999999999),
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": [
                "0x" + transactionData
            ]
        }
        # print("API_PostSendRawTransaction_StandardRPC " + shortName)
        response = requests.post(url, data=json.dumps(payload), headers=Headers, timeout=RequestTimeout_seconds)
        if response.ok:
            responseData = response.content
            jData = json.loads(responseData)
            print("API_PostSendRawTransaction_StandardRPC " + shortName + " jData = " + str(jData))

            if 'error' in jData:
                errorMessage = jData['error']['message']
                errorCode = jData['error']['code']
                # print("API_PostSendRawTransaction_StandardRPC " + shortName + " errorMessage: " + errorMessage + ". errorCode: " + str(errorCode))
                result[key] = jData['error']

            elif 'result' in jData:
                # print("API_PostSendRawTransaction_StandardRPC " + shortName + " jData = " + str(jData))
                transactionId = str(jData['result'])
                result[key] = transactionId

            else:
                print("No error or result in the response!")

        else:
            # If response code is not ok (200), print the resulting http error code with description
            response.raise_for_status()

    except:
        print("exception = " + traceback.format_exc())
        pass

    return result


def API_EstimateGas(toAddress, fromAddress, data, value=0, doAddExtraGasPadding=True, multiplier=1.22, timeout=RequestTimeout_seconds):
    value_hex = '0x' + ConvertIntToHex(int(value))
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_estimateGas",
        "params": [
            {
                "data": data,
                "to": toAddress,
                "from": fromAddress,
                "value": value_hex,
            },
        ]
    }

    if not toAddress:
        del payload['params'][0]['to']

    print("payload = " + str(payload))
    response = SendRequestToAllNodes(payload, Headers, timeout)
    if response.ok:
        responseData = response.content
        jData = json.loads(responseData)
        # print("jData = " + str(jData))
        estimatedGasUsage_wei = ConvertHexToInt(jData['result'])
        # print("estimatedGasUsage_wei = " + str(estimatedGasUsage_wei))
        if doAddExtraGasPadding:
            estimatedGasUsage_wei = int(estimatedGasUsage_wei * multiplier)
            # print("adding some extra gas as padding, estimatedGasUsage_wei = " + str(
            #     estimatedGasUsage_wei) + " after a multiplier of " + str(multiplier) + " was used")

        return estimatedGasUsage_wei

    else:
        # If response code is not ok (200), print the resulting http error code with description
        response.raise_for_status()


def IsAddressAValidDeployedContract(toAddress):
    try:
        result = API_GetCode(toAddress)
        if result != '0x':
            return True

    except (KeyboardInterrupt, SystemExit):
        print('\nkeyboard interrupt caught')
        print('\n...Program Stopped Manually!')
        raise

    except:
        message = "exception: " + traceback.format_exc()
        print(message)
        pass

    return False


def API_GetCode(toAddress):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [
            toAddress,
        ]
    }
    # print("payload = " + str(payload))
    response = SendRequestToAllNodes(payload, Headers, RequestTimeout_seconds)
    if response.ok:
        responseData = response.content
        jData = json.loads(responseData)
        return jData['result']

    else:
        # If response code is not ok (200), print the resulting http error code with description
        response.raise_for_status()


def SignTransaction(to, value, privkey, nonce=0, gas_int=21000, gasPrice_int=1010000000, data_hex=""):
    # print("SignTransaction gasPrice_int = " + str(ConvertWeiToGwei(gasPrice_int)) + " gwei")

    if not isinstance(gasPrice_int, int):
        raise Exception("gasPrice_int must be of type int")

    if gasPrice_int <= 0:
        raise Exception("gasPrice_int cannot be negative or zero")

    if not isinstance(gas_int, int):
        raise Exception("gas_int must be of type int")

    if gas_int <= 0:
        raise Exception("gas_int cannot be negative or zero")

    try:
        data_hex_with0xRemoved = data_hex.replace("0x", "")
        data = bytes.fromhex(data_hex_with0xRemoved)
        # Results in  {'error': True, 'message': ObjectSerializationError('Serialization failed because of field data ("Object is not a serializable (<class \'bytearray\'>)")',)}
        # data = bytearray.fromhex('deadbeef')
        # print("SignTransaction data = " + str(data))
        unsigned_transaction = transactions.Transaction(nonce, gasPrice_int, gas_int, to, value, data)
        # print("unsigned_transaction = " + str(unsigned_transaction))
        raw_transaction_bytes = rlp.encode(unsigned_transaction.sign(privkey))
        # print("raw_transaction_bytes = " + str(raw_transaction_bytes))
        raw_transaction_hex = Web3.toHex(raw_transaction_bytes)
        # print("raw_transaction_hex = " + str(raw_transaction_hex))
        raw_transaction_hex_0xRemoved = raw_transaction_hex.replace("0x", "")
        # print("raw_transaction_hex_0xRemoved = " + raw_transaction_hex_0xRemoved)
        return {'error': False, 'sign': raw_transaction_hex_0xRemoved}
    except Exception as msg:
        return {'error': True, 'message': msg}


def GetNullAddress():
    # NullAddress = Instance_Web3.toChecksumAddress("0x0000000000000000000000000000000000000000")
    from Libraries.nodes import Instance_Web3
    return Instance_Web3.toChecksumAddress("0x0000000000000000000000000000000000000000")


def GetEtherContractAddress():
    # EtherContractAddress = NullAddress
    return GetNullAddress()


def GetAddressFromDataProperty(dataProperty):
    return '0x' + dataProperty[-LengthOfPublicAddress_Excludes0x:]


def SplitStringIntoChunks(myStringIWantToSplit, splitLength):
    splitArray = [myStringIWantToSplit[i:i + splitLength] for i in range(0, len(myStringIWantToSplit), splitLength)]
    return splitArray


def ConvertGweiToWei(gwei):
    return int(gwei * 1000000000)


def ConvertWeiToGwei(wei):
    return wei / float(1000000000)


def ConvertHexToInt(hex):
    return int(hex, 16)


def IsStringATransactionId(myString):
    if not myString:
        return False

    if "0x" in str(myString) and len(str(myString)) != LengthOfTransactionHash_Including0x:
        return False

    if "0x" not in str(myString) and len(str(myString)) != LengthOfTransactionHash_Excludes0x:
        return False

    return True


def AllListItemsAreTheSame(items):
    return all(x == items[0] for x in items)
