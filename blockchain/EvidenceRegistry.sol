// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ============================================================
//  EvidenceRegistry.sol — SIH Digital Evidence Locker
//  Deploy on Polygon Amoy Testnet via https://remix.ethereum.org
// ============================================================
contract EvidenceRegistry {

    struct EvidenceRecord {
        string  caseId;
        string  docName;
        string  sha256Hash;
        address uploadedBy;
        uint256 timestamp;
    }

    mapping(string => EvidenceRecord) private records;

    event HashLogged(
        string indexed caseId,
        string docName,
        string sha256Hash,
        address uploadedBy,
        uint256 timestamp
    );

    function logEvidence(
        string memory caseId,
        string memory docName,
        string memory sha256Hash
    ) public {
        require(bytes(sha256Hash).length == 64, "Invalid SHA-256 hash");
        require(bytes(records[sha256Hash].sha256Hash).length == 0, "Already registered!");

        records[sha256Hash] = EvidenceRecord({
            caseId: caseId, docName: docName, sha256Hash: sha256Hash,
            uploadedBy: msg.sender, timestamp: block.timestamp
        });

        emit HashLogged(caseId, docName, sha256Hash, msg.sender, block.timestamp);
    }

    function verifyEvidence(string memory sha256Hash)
        public view returns (bool found, string memory caseId, string memory docName, uint256 timestamp)
    {
        EvidenceRecord memory r = records[sha256Hash];
        if (bytes(r.sha256Hash).length == 0) return (false, "", "", 0);
        return (true, r.caseId, r.docName, r.timestamp);
    }
}
