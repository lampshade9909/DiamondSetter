# Diamond Setter
Ethereum smart contract manager for the Diamond Standard

The Diamond Setter is a simple and effective contract manager for your Diamond Standard based contracts.  It makes maintaining and upgrading your contracts a breeze by automating the upgrade logic.  You simply provide your contract addresses and ABI and call the `set` command.  It automates the process of determining what needs upgraded/removed by calling the proper Diamond Standard functions.  

The Diamond Standard, [written by Nick Mudge](https://github.com/ethereum/EIPs/issues/2535), is a set of contracts that can access the same storage variables and while sharing the same Ethereum address to achieve upgradability and scalability.  [Nick discussed this new storage technique here](https://medium.com/1milliondevs/new-storage-layout-for-proxy-contracts-and-diamonds-98d01d0eadb) 


## Who should use the Diamond Setter?

Anyone currently using or planning on using the Diamond Standard.  Or anyone interested in Ethereum smart contract developemnt.  


## Diamond Setter features:

 * An automated control mechanism for upgrading and removing logic contracts
 * Built in safety features (so you don't accidentally overwrite something)  
 * Hashes your ds_slot strings


## How to use:
 1. Clone the repo.
 
 1. Set up your python environment with `virtualenv`.
 
 1. Install the python packages in `requirements.txt` file based on which OS you're using.
 
 1. Set up your config by copying the `diamondSetter_template.config` and creating your own personal `diamondSetter.config`.
 
 1. Add your contract ABI JSON files to the `Contracts` directory.  Make sure the file name exactly matches the contract name in the config.  The config file does not expect the `.json` extension.
 
 1. Set your mainnet deployed contract addresses in the config.      
 
 1. Use the `set` command to upgrade/remove contracts as you desire.
 

## Config

    [ACCOUNT]
    publicAddress = publicAddressGoesHere
    privateKey = privateKeyGoesHere
    gasPrice_gwei = 20
    
    [NODE]
    url = http://nodeUrlGoesHere:8545
    
    [CONTRACT_PROXY]
    filename = tutorial_proxy
    address = 0xfb1495fb3adca65a1c3374f206971891d3137ff9
    
    [CONTRACTS_LOGIC]
    tutorial_logic_a = 0xd37589ee0c581ef58efab0d2adb08d08b373125f
    tutorial_properties = 0xc630aae56ac54f52ee7fb757bf6b23f86a8aacea

The config specifies the names and addresses of your contracts.  The URL should be your ethereum node URL.  This can be a service like https://deploy.radar.tech/, https://infura.io/, https://alchemyapi.io/, or can simply point directly to your own personal node.     


## Commands
 
### Set
`python diamondSetter.py set`
    
    diamondCutDict_removes = {}
    diamondCutDict_updates = {'0xd37589ee0c581ef58efab0d2adb08d08b373125f': ['d22fd5fc', 'ba802cef'], '0xc630aae56ac54f52ee7fb757bf6b23f86a8aacea': ['a39fac12', 'c6ee701e', 'b9571721', '1b5fc9a1']}
    Merged diamondCutDict_merged and diamondCutDict_merged
    diamondCutDict_merged = {'0xd37589ee0c581ef58efab0d2adb08d08b373125f': ['d22fd5fc', 'ba802cef'], '0xc630aae56ac54f52ee7fb757bf6b23f86a8aacea': ['a39fac12', 'c6ee701e', 'b9571721', '1b5fc9a1']}
    Do you want to execute this API_DiamondCut?  y/n:  y
    
In this case, no removes were necessary and several updates were necessary.  The two addresses you see in `diamondCutDict_updates` are the logic contracts that need updated in the proxy contract.  The array following is showing which function selectors are being registered with the proxy contract.  `diamondCutDict_merged` is where it merges removes with updates so that you can remove and update in one single transaction.

You can view the transaction here: 
https://etherscan.io/tx/0x6fa3da9f80c1ee3f7d4128c866a3fd98c9f6a7d18e09980fe3f9303c141e20f2    


### Hash
`python diamondSetter.py hash diamond.storage.tutorial.properties`
    
    // NOTE: this ds_slot must be the shared if you want to share storage with another contract under the proxy umbrella
    // NOTE: this ds_slot must be unique if you want to NOT share storage with another contract under the proxy umbrella
    // ds_slot = keccak256(diamond.storage.tutorial.properties);
    assembly { ds_slot := 0x8009ef9e316d149758ddd03fd4cb6dd67f0acee3d8cdf1372cf6f2ac6d689dbd }

This assembly code gets added to your solidity smart contract.  I've included some important comments to help you ensure you're using the `ds_slot` properly.  Using the same `ds_slot` across multiple contracts will enable sharing of storage.  Using a unique `ds_slot` prevents sharing.  The sharing is all within the proxy contract umbrella.  Only contracts under the proxy umbrella can share storage.


## When to share storage
Including a `ds_slot` in more than one contract enables sharing storage between those contracts.  You'll want to do this when you're deploying many contracts that all want to reference the same storage variables.  An example is found here when the `StorageContract_Properties` are used both in the [Tutorial_Logic_A](https://github.com/lampshade9909/DiamondSetter/blob/063b02b732a2407beeaf5d2488fa5886d47d2eb5/Contracts/tutorial_logic_a.sol#L39) contract and [Tutorial_Properties](https://github.com/lampshade9909/DiamondSetter/blob/063b02b732a2407beeaf5d2488fa5886d47d2eb5/Contracts/tutorial_properties.sol#L39) contract.  Notice that in both cases the `ds_slot` is exactly `0x8009ef9e316d149758ddd03fd4cb6dd67f0acee3d8cdf1372cf6f2ac6d689dbd`.  


## How to intentionally overwrite/remove
To intentionally overwrite or remove a contract from the proxy, [simply add the contract's address here](https://github.com/lampshade9909/DiamondSetter/blob/7e298b4235b4dbb7ed7e78a422f830e202a6b521/Libraries/set.py#L71).  This tells the `set` command that it's allowed to remove or overwrite this contract's function selectors.  


## A danger to be aware of
Be careful that you do not upgrade yourself out of your own contract!  This software takes steps to prevent that from happening accidentally, but it is still possible.  One critical known way this can be achieved is by overwriting the proxy owner function selector.  Say you use the property `address owner` as the proxy owner.  It is possible for you to make a diamond cut and delegate that same exact function selector to a logic contract.  This is bad because this prevents you from accessing the proxy function's owner.  Depending on your logic, that may lock you out of your own proxy!

The `set` command's safety measure will help protect you from doing this by accident, but here are some additional steps I take to help prevent this from happening

 1. Make the `address owner` an extremely unique string.  Instead of just using the word `owner`, give it something that is extremely unlikely to collide with anything in the future when you're upgrading.  In this example, I used [owner_Proxy_ThisNameMustBeUniqueBecauseInTheoryItCouldGetOverridenByALogicContractHavingTheSameFunctionSelector](https://github.com/lampshade9909/DiamondSetter/blob/7e298b4235b4dbb7ed7e78a422f830e202a6b521/Contracts/tutorial_proxy.sol#L88).  Chances are, you won't accidentally type that in a logic contract during a future contract upgrade ;-)
 
 1. Have both a proxy owner and a logic contract owner.  In this example, I also included [a whitelisted group of users](https://github.com/lampshade9909/DiamondSetter/blob/7e298b4235b4dbb7ed7e78a422f830e202a6b521/Contracts/tutorial_proxy.sol#L33) who have ownership over the logic contracts underneath the proxy.  Then you can give these users permission to withdraw assets.  Now, if for some reason you get locked out in one place you can always escape your assets via the other place.  Example: you upgrade yourself out of proxy owner control, you can simply withdraw your assets via the logic contract owner control.  And alternatively, if you accidentally upgrade yourself out of control of the logic contracts, you still have control of the proxy contracts so you can upgrade yourself back in control.  
 
 Obviously this depends on what you're trying to build.  But these are some helpful ideas.       


## Contact:

http://JoeyZacherl.com/

Joey.Zacherl@gmail.com


## License:
MIT license. See the license file. Anyone can use or modify this software for their purposes.