import random
import string
from enum import Enum

from Libraries.core import API_GetTransactionCount


class TransactionType(Enum):
    trade = 1
    approve = 2
    deposit = 3
    withdraw = 4
    cancelOrder = 5
    other = 6
    deploy = 7


def API_SendEther_ToContract(fromAddress, fromPrivateKey, sendToAddress, value, gas_int, gasPrice_int,
                             data_hex, transactionType, nonce=None):
    from Libraries.core import SignTransaction, API_SendRawTransaction_ToManyRemoteNodes

    if not sendToAddress:
        # We can only allow sendToAddress to not be set if we're deploying a contract
        if transactionType == TransactionType.deploy:
            pass
        else:
            print("sendToAddress is None! Failed to API_SendEther_ToContract")
            return None

    if not fromAddress:
        print("fromAddress is None! Failed to API_SendEther_ToContract")
        return None

    # print("API_SendEther_ToContract fromAddress: " + fromAddress + ", sendToAddress: " + sendToAddress)

    transactionCount = None
    # We cannot call API_GetTransactionCount if this fromAddress has not yet made a transaction,
    # because the call will error out because the account hasn't yet been used
    # This makes for some awkward logic, my work around is this, don't call it if nonce is hard coded to zero!
    if nonce != 0:
        # Get the transactionCount for the nonce
        transactionCount = API_GetTransactionCount(fromAddress)

    nonceToUse = None
    # If we're using a zero nonce
    if nonce == 0:
        # Set nonceToUse and do not look at transactionCount at all, since we cannot make the call because it will fail
        nonceToUse = nonce
    # If we're just using the transactionCount as the nonce
    elif not nonce:
        print("using nonce from transactionCount: " + str(transactionCount))
        nonceToUse = transactionCount
    # If we're going to override the nonce to something specific (either future or current)
    else:
        print("using hard coded nonce = " + str(nonce) + ", while transactionCount = " + str(transactionCount))
        nonceToUse = nonce

        if nonceToUse < transactionCount:
            # TODO, I'm not sure if I should throw an exception here.  I want to see if this ever happens before I start throwing exceptions.  This may never happen...
            message = "GetNonceToUseForQueueableTransaction: Nonce invalid.  Overriding to transactionCount. transactionCount = " + str(
                transactionCount) + " yet nonceToUse was calculated to be = " + str(
                nonceToUse) + ". nonceToUse should never be less than transactionCount. I must have a bug."
            print(message)

            # override the nonce because our nonceToUse was less than the transactionCount and that shouldn't happen.
            # If this did happen, than lots of transactions must be flying around and blocks must be getting mined in real quick within the last few seconds
            nonceToUse = transactionCount

    # Send the transaction, consider trying again under certain circumstances
    result = SignTransaction(sendToAddress, value, fromPrivateKey, nonceToUse, gas_int, gasPrice_int, data_hex)

    error = result['error']
    print("transactionHash error = " + str(error))
    if error:
        print("transactionHash result = " + str(result))

    signedTransactionHash = result['sign']
    # print("signedTransactionHash = " + signedTransactionHash)

    transactionId, broadcastError = API_SendRawTransaction_ToManyRemoteNodes(signedTransactionHash)
    print("transactionId: " + str(transactionId) + ", broadcastError: " + str(broadcastError))

    # Trash the fromPrivateKey in memory
    fromPrivateKey = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(101))

    return transactionId
