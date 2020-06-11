pragma solidity ^0.6.4;
pragma experimental ABIEncoderV2;

/******************************************************************************\
* Original Author: Nick Mudge (modified by Joey Zacherl)
*
* Implementation of a Diamond.
* This is gas optimized by reducing storage reads and storage writes.
/******************************************************************************/

interface Diamond
{
    /// @notice _diamondCut is an array of bytes arrays.
    /// This argument is tightly packed for gas efficiency.
    /// That means no padding with zeros.
    /// Here is the structure of _diamondCut:
    /// _diamondCut = [
    ///     abi.encodePacked(facet, sel1, sel2, sel3, ...),
    ///     abi.encodePacked(facet, sel1, sel2, sel4, ...),
    ///     ...
    /// ]
    /// facet is the address of a facet
    /// sel1, sel2, sel3 etc. are four-byte function selectors.
    function diamondCut(bytes[] calldata _diamondCut) external;
    event DiamondCut(bytes[] _diamondCut);
}

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

contract StorageContract_Proxy
{
    struct DiamondStorage_Proxy
    {
        // maps function selectors to the facets that execute the functions.
        // and maps the selectors to the slot in the selectorSlots array.
        // and maps the selectors to the position in the slot.
        // func selector => address facet, uint64 slotsIndex, uint64 slotIndex
        mapping(bytes4 => bytes32) facets;

        // array of slots of function selectors.
        // each slot holds 8 function selectors.
        mapping(uint => bytes32) selectorSlots;

        // uint128 numSelectorsInSlot, uint128 selectorSlotsLength
        // selectorSlotsLength is the number of 32-byte slots in selectorSlots.
        // selectorSlotLength is the number of selectors in the last slot of
        // selectorSlots.
        uint selectorSlotsLength;

        // Used to query if a contract implements an interface.
        // Used to implement ERC-165.
        mapping(bytes4 => bool) supportedInterfaces;
    }

    function diamondStorage_Proxy() internal pure returns(DiamondStorage_Proxy storage ds)
    {
        // NOTE: this ds_slot must be the shared if you want to share storage with another contract under the proxy umbrella
        // NOTE: this ds_slot must be unique if you want to NOT share storage with another contract under the proxy umbrella
        // ds_slot = keccak256(diamond.storage.tutorial.proxy);
        assembly { ds_slot := 0x974f3cfcf513e09347459922e3dfbf4842f090ee6f9ab895dd61cec8b4be1a22 }
    }
}

contract Owned is
    StorageContract_Authentication
{
    // I'm naming this varible to be super unique so that nother ever overwrites it!
    // Unless this name gets re-used again which should never happen...
    // Be careful, logic contracts under this proxy umbrella could potentially overwrite this
    // owner address method selector causing this owner to be lost!
    // So it's critical to NEVER overwrite this function selector when you're upgrading a logic contract.
    // In other words, never re-use this long unique name
    address public owner_Proxy_ThisNameMustBeUniqueBecauseInTheoryItCouldGetOverridenByALogicContractHavingTheSameFunctionSelector;

    constructor() public
    {
        owner_Proxy_ThisNameMustBeUniqueBecauseInTheoryItCouldGetOverridenByALogicContractHavingTheSameFunctionSelector = msg.sender;
    }

    modifier onlyOwner()
    {
        require(msg.sender == owner_Proxy_ThisNameMustBeUniqueBecauseInTheoryItCouldGetOverridenByALogicContractHavingTheSameFunctionSelector, "Must own the contract.");
        _;
    }

    function whitelistUsers (
        address[] memory users,
        bool value
        ) public onlyOwner
    {
        // Only the owner can modify the whitelist
        DiamondStorage_Authentication storage ds = diamondStorage_Authentication();

        for(uint i = 0; i < users.length; i++)
		{
		    ds.whitelistedUsers[users[i]] = value;
		}
    }
}

contract DiamondFacet is
    Owned,
    StorageContract_Proxy,
    Diamond
{
    bytes32 constant CLEAR_ADDRESS_MASK = 0x0000000000000000000000000000000000000000ffffffffffffffffffffffff;
    bytes32 constant CLEAR_SELECTOR_MASK = 0xffffffff00000000000000000000000000000000000000000000000000000000;

    struct SlotInfo
    {
        uint originalSelectorSlotsLength;
        bytes32 selectorSlot;
        uint oldSelectorSlotsIndex;
        uint oldSelectorSlotIndex;
        bytes32 oldSelectorSlot;
        bool newSlot;
    }

    function diamondCut(
        bytes[] memory _diamondCut
        ) public onlyOwner override
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();

        SlotInfo memory slot;
        slot.originalSelectorSlotsLength = ds.selectorSlotsLength;
        uint selectorSlotsLength = uint128(slot.originalSelectorSlotsLength);
        uint selectorSlotLength = uint128(slot.originalSelectorSlotsLength >> 128);
        if(selectorSlotLength > 0)
        {
            slot.selectorSlot = ds.selectorSlots[selectorSlotsLength];
        }
        // loop through diamond cut
        for(uint diamondCutIndex; diamondCutIndex < _diamondCut.length; diamondCutIndex++)
        {
            bytes memory facetCut = _diamondCut[diamondCutIndex];
            require(facetCut.length > 20, "Missing facet or selector info.");
            bytes32 currentSlot;
            assembly
            {
                currentSlot := mload(add(facetCut,32))
            }
            bytes32 newFacet = bytes20(currentSlot);
            uint numSelectors = (facetCut.length - 20) / 4;
            uint position = 52;

            // adding or replacing functions
            if(newFacet != 0)
            {
                // add and replace selectors
                for(uint selectorIndex; selectorIndex < numSelectors; selectorIndex++)
                {
                    bytes4 selector;
                    assembly
                    {
                        selector := mload(add(facetCut,position))
                    }
                    position += 4;
                    bytes32 oldFacet = ds.facets[selector];
                    // add
                    if(oldFacet == 0)
                    {
                        ds.facets[selector] = newFacet | bytes32(selectorSlotLength) << 64 | bytes32(selectorSlotsLength);
                        slot.selectorSlot = slot.selectorSlot & ~(CLEAR_SELECTOR_MASK >> selectorSlotLength * 32) | bytes32(selector) >> selectorSlotLength * 32;
                        selectorSlotLength++;
                        if(selectorSlotLength == 8)
                        {
                            ds.selectorSlots[selectorSlotsLength] = slot.selectorSlot;
                            slot.selectorSlot = 0;
                            selectorSlotLength = 0;
                            selectorSlotsLength++;
                            slot.newSlot = false;
                        }
                        else
                        {
                            slot.newSlot = true;
                        }
                    }
                    // replace
                    else
                    {
                        require(bytes20(oldFacet) != bytes20(newFacet), "Function cut to same facet.");
                        ds.facets[selector] = oldFacet & CLEAR_ADDRESS_MASK | newFacet;
                    }
                }
            }
            // remove functions
            else
            {
                for(uint selectorIndex; selectorIndex < numSelectors; selectorIndex++)
                {
                    bytes4 selector;
                    assembly
                    {
                        selector := mload(add(facetCut,position))
                    }
                    position += 4;
                    bytes32 oldFacet = ds.facets[selector];
                    require(oldFacet != 0, "Function doesn't exist. Can't remove.");
                    if(slot.selectorSlot == 0)
                    {
                        selectorSlotsLength--;
                        slot.selectorSlot = ds.selectorSlots[selectorSlotsLength];
                        selectorSlotLength = 8;
                    }
                    slot.oldSelectorSlotsIndex = uint64(uint(oldFacet));
                    slot.oldSelectorSlotIndex = uint32(uint(oldFacet >> 64));
                    bytes4 lastSelector = bytes4(slot.selectorSlot << (selectorSlotLength-1) * 32);
                    if(slot.oldSelectorSlotsIndex != selectorSlotsLength)
                    {
                        slot.oldSelectorSlot = ds.selectorSlots[slot.oldSelectorSlotsIndex];
                        slot.oldSelectorSlot = slot.oldSelectorSlot & ~(CLEAR_SELECTOR_MASK >> slot.oldSelectorSlotIndex * 32) | bytes32(lastSelector) >> slot.oldSelectorSlotIndex * 32;
                        ds.selectorSlots[slot.oldSelectorSlotsIndex] = slot.oldSelectorSlot;
                        selectorSlotLength--;
                    }
                    else
                    {
                        slot.selectorSlot = slot.selectorSlot & ~(CLEAR_SELECTOR_MASK >> slot.oldSelectorSlotIndex * 32) | bytes32(lastSelector) >> slot.oldSelectorSlotIndex * 32;
                        selectorSlotLength--;
                    }
                    if(selectorSlotLength == 0)
                    {
                        delete ds.selectorSlots[selectorSlotsLength];
                        slot.selectorSlot = 0;
                    }
                    if(lastSelector != selector)
                    {
                        ds.facets[lastSelector] = oldFacet & CLEAR_ADDRESS_MASK | bytes20(ds.facets[lastSelector]);
                    }
                    delete ds.facets[selector];
                }
            }
        }
        uint newSelectorSlotsLength = selectorSlotLength << 128 | selectorSlotsLength;
        if(newSelectorSlotsLength != slot.originalSelectorSlotsLength)
        {
            ds.selectorSlotsLength = newSelectorSlotsLength;
        }
        if(slot.newSlot)
        {
            ds.selectorSlots[selectorSlotsLength] = slot.selectorSlot;
        }
        emit DiamondCut(_diamondCut);
    }
}

// A loupe is a small magnifying glass used to look at diamonds.
// These functions look at diamonds
interface DiamondLoupe
{
    /// These functions are expected to be called frequently
    /// by tools. Therefore the return values are tightly
    /// packed for efficiency. That means no padding with zeros.

    /// @notice Gets all facets and their selectors.
    /// @return An array of bytes arrays containing each facet
    ///         and each facet's selectors.
    /// The return value is tightly packed.
    /// Here is the structure of the return value:
    /// returnValue = [
    ///     abi.encodePacked(facet, sel1, sel2, sel3, ...),
    ///     abi.encodePacked(facet, sel1, sel2, sel3, ...),
    ///     ...
    /// ]
    /// facet is the address of a facet.
    /// sel1, sel2, sel3 etc. are four-byte function selectors.
    function facets() external view returns(bytes[] memory);

    /// @notice Gets all the function selectors supported by a specific facet.
    /// @param _facet The facet address.
    /// @return A byte array of function selectors.
    /// The return value is tightly packed. Here is an example:
    /// return abi.encodePacked(selector1, selector2, selector3, ...)
    function facetFunctionSelectors(address _facet) external view returns(bytes memory);

    /// @notice Get all the facet addresses used by a diamond.
    /// @return A byte array of tightly packed facet addresses.
    /// Example return value:
    /// return abi.encodePacked(facet1, facet2, facet3, ...)
    function facetAddresses() external view returns(bytes memory);

    /// @notice Gets the facet that supports the given selector.
    /// @dev If facet is not found return address(0).
    /// @param _functionSelector The function selector.
    /// @return The facet address.
    function facetAddress(bytes4 _functionSelector) external view returns(address);
}

interface ERC165
{
    /// @notice Query if a contract implements an interface
    /// @param interfaceID The interface identifier, as specified in ERC-165
    /// @dev Interface identification is specified in ERC-165. This function
    ///  uses less than 30,000 gas.
    /// @return `true` if the contract implements `interfaceID` and
    ///  `interfaceID` is not 0xffffffff, `false` otherwise
    function supportsInterface(bytes4 interfaceID) external view returns (bool);
}

contract DiamondLoupeFacet is DiamondLoupe, StorageContract_Proxy
{
    /// These functions are expected to be called frequently
    /// by tools. Therefore the return values are tightly
    /// packed for efficiency. That means no padding with zeros.

    struct Facet
    {
        address facet;
        bytes4[] functionSelectors;
    }

    /// @notice Gets all facets and their selectors.
    /// @return An array of bytes arrays containing each facet
    ///         and each facet's selectors.
    /// The return value is tightly packed.
    /// That means no padding with zeros.
    /// Here is the structure of the return value:
    /// returnValue = [
    ///     abi.encodePacked(facet, sel1, sel2, sel3, ...),
    ///     abi.encodePacked(facet, sel1, sel2, sel3, ...),
    ///     ...
    /// ]
    /// facet is the address of a facet.
    /// sel1, sel2, sel3 etc. are four-byte function selectors.
    function facets(
        ) external view override returns(bytes[] memory)
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();
        uint totalSelectorSlots = ds.selectorSlotsLength;
        uint selectorSlotLength = uint128(totalSelectorSlots >> 128);
        totalSelectorSlots = uint128(totalSelectorSlots);
        uint totalSelectors = totalSelectorSlots * 8 + selectorSlotLength;
        if(selectorSlotLength > 0)
        {
            totalSelectorSlots++;
        }

        // get default size of arrays
        uint defaultSize = totalSelectors;
        if(defaultSize > 20)
        {
            defaultSize = 20;
        }
        Facet[] memory facets_ = new Facet[](defaultSize);
        uint8[] memory numFacetSelectors = new uint8[](defaultSize);
        uint numFacets;
        uint selectorCount;
        // loop through function selectors
        for(uint slotIndex; selectorCount < totalSelectors; slotIndex++)
        {
            bytes32 slot = ds.selectorSlots[slotIndex];
            for(uint selectorIndex; selectorIndex < 8; selectorIndex++)
            {
                selectorCount++;
                if(selectorCount > totalSelectors)
                {
                    break;
                }
                bytes4 selector = bytes4(slot << selectorIndex * 32);
                address facet = address(bytes20(ds.facets[selector]));
                bool continueLoop = false;
                for(uint facetIndex; facetIndex < numFacets; facetIndex++)
                {
                    if(facets_[facetIndex].facet == facet)
                    {
                        uint arrayLength = facets_[facetIndex].functionSelectors.length;
                        // if array is too small then enlarge it
                        if(numFacetSelectors[facetIndex]+1 > arrayLength)
                        {
                            bytes4[] memory biggerArray = new bytes4[](arrayLength + defaultSize);
                            // copy contents of old array
                            for(uint i; i < arrayLength; i++)
                            {
                                biggerArray[i] = facets_[facetIndex].functionSelectors[i];
                            }
                            facets_[facetIndex].functionSelectors = biggerArray;
                        }
                        facets_[facetIndex].functionSelectors[numFacetSelectors[facetIndex]] = selector;
                        // probably will never have more than 255 functions from one facet contract
                        require(numFacetSelectors[facetIndex] < 255);
                        numFacetSelectors[facetIndex]++;
                        continueLoop = true;
                        break;
                    }
                }
                if(continueLoop)
                {
                    continueLoop = false;
                    continue;
                }
                uint arrayLength = facets_.length;
                // if array is too small then enlarge it
                if(numFacets+1 > arrayLength)
                {
                    Facet[] memory biggerArray = new Facet[](arrayLength + defaultSize);
                    uint8[] memory biggerArray2 = new uint8[](arrayLength + defaultSize);
                    for(uint i; i < arrayLength; i++)
                    {
                        biggerArray[i] = facets_[i];
                        biggerArray2[i] = numFacetSelectors[i];
                    }
                    facets_ = biggerArray;
                    numFacetSelectors = biggerArray2;
                }
                facets_[numFacets].facet = facet;
                facets_[numFacets].functionSelectors = new bytes4[](defaultSize);
                facets_[numFacets].functionSelectors[0] = selector;
                numFacetSelectors[numFacets] = 1;
                numFacets++;
            }
        }
        bytes[] memory returnFacets = new bytes[](numFacets);
        for(uint facetIndex; facetIndex < numFacets; facetIndex++)
        {
            uint numSelectors = numFacetSelectors[facetIndex];
            bytes memory selectorsBytes = new bytes(4 * numSelectors);
            bytes4[] memory selectors = facets_[facetIndex].functionSelectors;
            uint bytePosition;
            for(uint i; i < numSelectors; i++)
            {
                for(uint j; j < 4; j++)
                {
                    selectorsBytes[bytePosition] = byte(selectors[i] << j * 8);
                    bytePosition++;
                }
            }
            returnFacets[facetIndex] = abi.encodePacked(facets_[facetIndex].facet, selectorsBytes);
        }
        return returnFacets;
    }

    /// @notice Gets all the function selectors supported by a specific facet.
    /// @param _facet The facet address.
    /// @return A bytes array of function selectors.
    /// The return value is tightly packed. Here is an example:
    /// return abi.encodePacked(selector1, selector2, selector3, ...)
    function facetFunctionSelectors(
        address _facet
        ) external view override returns(bytes memory)
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();
        uint totalSelectorSlots = ds.selectorSlotsLength;
        uint selectorSlotLength = uint128(totalSelectorSlots >> 128);
        totalSelectorSlots = uint128(totalSelectorSlots);
        uint totalSelectors = totalSelectorSlots * 8 + selectorSlotLength;
        if(selectorSlotLength > 0)
        {
            totalSelectorSlots++;
        }

        uint numFacetSelectors;
        bytes4[] memory facetSelectors = new bytes4[](totalSelectors);
        uint selectorCount;
        // loop through function selectors
        for(uint slotIndex; selectorCount < totalSelectors; slotIndex++)
        {
            bytes32 slot = ds.selectorSlots[slotIndex];
            for(uint selectorIndex; selectorIndex < 8; selectorIndex++)
            {
                selectorCount++;
                if(selectorCount > totalSelectors)
                {
                    break;
                }
                bytes4 selector = bytes4(slot << selectorIndex * 32);
                address facet = address(bytes20(ds.facets[selector]));
                if(_facet == facet)
                {
                    facetSelectors[numFacetSelectors] = selector;
                    numFacetSelectors++;
                }
            }
        }
        bytes memory returnBytes = new bytes(4 * numFacetSelectors);
        uint bytePosition;
        for(uint i; i < numFacetSelectors; i++)
        {
            for(uint j; j < 4; j++)
            {
                returnBytes[bytePosition] = byte(facetSelectors[i] << j * 8);
                bytePosition++;
            }
        }
        return returnBytes;
    }

    /// @notice Get all the facet addresses used by a diamond.
    /// @return A byte array of tightly packed facet addresses.
    /// Example return value:
    /// return abi.encodePacked(facet1, facet2, facet3, ...)
    function facetAddresses(
        ) external view override returns(bytes memory)
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();
        uint totalSelectorSlots = ds.selectorSlotsLength;
        uint selectorSlotLength = uint128(totalSelectorSlots >> 128);
        totalSelectorSlots = uint128(totalSelectorSlots);
        uint totalSelectors = totalSelectorSlots * 8 + selectorSlotLength;
        if(selectorSlotLength > 0)
        {
            totalSelectorSlots++;
        }
        address[] memory facets_ = new address[](totalSelectors);
        uint numFacets;
        uint selectorCount;
        // loop through function selectors
        for(uint slotIndex; selectorCount < totalSelectors; slotIndex++)
        {
            bytes32 slot = ds.selectorSlots[slotIndex];
            for(uint selectorIndex; selectorIndex < 8; selectorIndex++)
            {
                selectorCount++;
                if(selectorCount > totalSelectors)
                {
                    break;
                }
                bytes4 selector = bytes4(slot << selectorIndex * 32);
                address facet = address(bytes20(ds.facets[selector]));
                bool continueLoop = false;
                for(uint facetIndex; facetIndex < numFacets; facetIndex++)
                {
                    if(facet == facets_[facetIndex])
                    {
                        continueLoop = true;
                        break;
                    }
                }
                if(continueLoop)
                {
                    continueLoop = false;
                    continue;
                }
                facets_[numFacets] = facet;
                numFacets++;
            }
        }

        bytes memory returnBytes = new bytes(20 * numFacets);
        uint bytePosition;
        for(uint i; i < numFacets; i++)
        {
            for(uint j; j < 20; j++)
            {
                returnBytes[bytePosition] = byte(bytes20(facets_[i]) << j * 8);
                bytePosition++;
            }
        }
        return returnBytes;
    }

    /// @notice Gets the facet that supports the given selector.
    /// @dev If facet is not found return address(0).
    /// @param _functionSelector The function selector.
    /// @return The facet address.
    function facetAddress(
        bytes4 _functionSelector
        ) external view override returns(address)
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();
        return address(bytes20(ds.facets[_functionSelector]));
    }
}

contract TutorialProxy is
    Owned,
    StorageContract_Proxy
{
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor(
        ) public
    {
        emit OwnershipTransferred(address(0), msg.sender);

        // Whitelist the contract creator
        DiamondStorage_Authentication storage ds_Authentication = diamondStorage_Authentication();
	    ds_Authentication.whitelistedUsers[msg.sender] = true;

        // Create a DiamondFacet contract which implements the Diamond interface
        DiamondFacet diamondFacet = new DiamondFacet();

        // Create a DiamondLoupeFacet contract which implements the Diamond Loupe interface
        DiamondLoupeFacet diamondLoupeFacet = new DiamondLoupeFacet();

        bytes[] memory diamondCut = new bytes[](3);

        // Adding cut function
        diamondCut[0] = abi.encodePacked(diamondFacet, Diamond.diamondCut.selector);

        // Adding diamond loupe functions
        diamondCut[1] = abi.encodePacked(
            diamondLoupeFacet,
            DiamondLoupe.facetFunctionSelectors.selector,
            DiamondLoupe.facets.selector,
            DiamondLoupe.facetAddress.selector,
            DiamondLoupe.facetAddresses.selector
        );

        // Adding supportsInterface function
        diamondCut[2] = abi.encodePacked(address(this), ERC165.supportsInterface.selector);

        // execute cut function
        bytes memory cutFunction = abi.encodeWithSelector(Diamond.diamondCut.selector, diamondCut);
        (bool success,) = address(diamondFacet).delegatecall(cutFunction);
        require(success, "Adding functions failed.");

        // adding ERC165 data
        DiamondStorage_Proxy storage ds_Proxy = diamondStorage_Proxy();
        ds_Proxy.supportedInterfaces[ERC165.supportsInterface.selector] = true;
        ds_Proxy.supportedInterfaces[Diamond.diamondCut.selector] = true;
        bytes4 interfaceID = DiamondLoupe.facets.selector ^ DiamondLoupe.facetFunctionSelectors.selector ^ DiamondLoupe.facetAddresses.selector ^ DiamondLoupe.facetAddress.selector;
        ds_Proxy.supportedInterfaces[interfaceID] = true;
    }

    // This is an immutable functions because it is defined directly in the diamond.
    // This implements ERC-165.
    function supportsInterface(
        bytes4 _interfaceID
        ) external view returns (bool)
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();
        return ds.supportedInterfaces[_interfaceID];
    }

    // Finds facet for function that is called and executes the
    // function if it is found and returns any value.
    fallback() external payable
    {
        DiamondStorage_Proxy storage ds = diamondStorage_Proxy();
        address facet = address(bytes20(ds.facets[msg.sig]));
        require(facet != address(0), "Function does not exist.");
        assembly
        {
            let ptr := mload(0x40)
            calldatacopy(ptr, 0, calldatasize())
            let result := delegatecall(gas(), facet, ptr, calldatasize(), 0, 0)
            let size := returndatasize()
            returndatacopy(ptr, 0, size)
            switch result
            case 0 {revert(ptr, size)}
            default {return (ptr, size)}
        }
    }

    receive() external payable {}
}
