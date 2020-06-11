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

contract Tutorial_Properties is
    StorageContract_Properties,
    WhitelistedOwners
{
    function setAddresses(
        address[] memory addressArray
        ) public onlyWhitelist
    {
        DiamondStorage_Properties storage ds = diamondStorage_Properties();
        uint256 i = 0;

        ds.address1 = addressArray[i++];
        ds.address2 = addressArray[i++];
    }

    function setInts(
        uint256[] memory intArray
        ) public onlyWhitelist
    {
        DiamondStorage_Properties storage ds = diamondStorage_Properties();
        uint256 i = 0;

        ds.doLogEvents = intArray[i++];
        ds.number1 = intArray[i++];
        ds.number2 = intArray[i++];
    }

    function getAddresses(
        ) public view returns (address[] memory addressArray)
    {
        DiamondStorage_Properties storage ds = diamondStorage_Properties();
        uint256 i = 0;
        addressArray = new address[](2);  // NOTE, Update this fixed array size as you add items!

        addressArray[i++] = ds.address1;
        addressArray[i++] = ds.address2;

        return addressArray;
    }

    function getInts(
        ) public view returns (uint256[] memory intArray)
    {
        DiamondStorage_Properties storage ds = diamondStorage_Properties();
        uint256 i = 0;
        intArray = new uint256[](3);  // NOTE, Update this fixed array size as you add items!

        intArray[i++] = ds.doLogEvents;
        intArray[i++] = ds.number1;
        intArray[i++] = ds.number2;

        return intArray;
    }
}
