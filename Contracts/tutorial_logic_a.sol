pragma solidity ^0.6.4;
pragma experimental "ABIEncoderV2";

contract StorageContract_Authentication
{
    struct DiamondStorage_Authentication
    {
        // This should NEVER be modified outside of the proxy
        mapping (address => bool) whitelistedUsers;
    }

    function diamondStorage_Authentication() internal pure returns(DiamondStorage_Authentication storage ds)
    {
        // NOTE: this ds_slot must be the shared if you want to share storage with another contract under the proxy umbrella
        // NOTE: this ds_slot must be unique if you want to NOT share storage with another contract under the proxy umbrella
        // ds_slot = keccak256(diamond.storage.tutorial.authentication);
        assembly { ds_slot := 0x32878c5ae2e5bc11f376d2263f2fd5b58a6491377bb89e17008861062e9c4bb0 }
    }
}

contract StorageContract_Properties
{
    struct DiamondStorage_Properties
    {
        // addressArray
        address address1;
        address address2;

        // intArray
        uint256 doLogEvents;  // 1 means yes, 0 means no
        uint256 number1;
        uint256 number2;
    }

    function diamondStorage_Properties() internal pure returns(DiamondStorage_Properties storage ds)
    {
        // NOTE: this ds_slot must be the shared if you want to share storage with another contract under the proxy umbrella
        // NOTE: this ds_slot must be unique if you want to NOT share storage with another contract under the proxy umbrella
        // ds_slot = keccak256(diamond.storage.tutorial.properties);
        assembly { ds_slot := 0x8009ef9e316d149758ddd03fd4cb6dd67f0acee3d8cdf1372cf6f2ac6d689dbd }
    }
}

contract WhitelistedOwners is
    StorageContract_Authentication
{
    modifier onlyWhitelist()
    {
        DiamondStorage_Authentication storage ds = diamondStorage_Authentication();
        require(ds.whitelistedUsers[msg.sender] == true, "Must be whitelisted.");
        _;
    }
}

contract Logs is
    StorageContract_Properties
{
    event Event_LogValue(uint256 value);

    function logValue_ifEnabled(
        uint256 value
        ) internal
    {
        DiamondStorage_Properties storage ds = diamondStorage_Properties();
        if (ds.doLogEvents == 1)
        {
            emit Event_LogValue(value);
        }
    }
}

contract Tutorial is
    WhitelistedOwners,
    Logs
{

    function superPublicThing(
        ) external returns(uint256)
    {
        DiamondStorage_Properties storage ds = diamondStorage_Properties();

        // Not using SafeMath, living life on the edge
        uint256 returnValue = ds.number1 + ds.number2;
        logValue_ifEnabled(returnValue);
        return returnValue;
    }

    function superSecretThing(
        ) external onlyWhitelist returns(uint256)
    {
        return 1337;
    }

}
