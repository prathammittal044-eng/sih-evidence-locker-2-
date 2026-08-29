// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceRegistry {
    // Ultra gas-optimized mapping: uint256 ID -> bytes32 hash (takes exactly 1 storage slot)
    mapping(uint256 => bytes32) public evidenceHashes;
    
    event EvidenceLogged(uint256 indexed id, bytes32 fileHash, address indexed loggedBy);
    
    function logEvidence(uint256 _id, bytes32 _fileHash) public {
        // Only 1 state write (SSTORE) = drastically reduced gas cost
        require(evidenceHashes[_id] == bytes32(0), "Already logged");
        evidenceHashes[_id] = _fileHash;
        
        // Emitting events is 10x cheaper than storing variables like timestamp and address
        emit EvidenceLogged(_id, _fileHash, msg.sender);
    }
    
    function verifyEvidence(uint256 _id, bytes32 _fileHash) public view returns (bool) {
        require(evidenceHashes[_id] != bytes32(0), "Not found");
        return evidenceHashes[_id] == _fileHash;
    }
}
