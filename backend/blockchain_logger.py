"""
blockchain_logger.py - Polygon Blockchain Integration
Logs every uploaded document hash to the Polygon Amoy Testnet permanently.
No one can tamper with evidence hashes once they are on the blockchain.
"""
import os
from dotenv import load_dotenv

_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_backend_dir, ".env"))

BLOCKCHAIN_AVAILABLE = False
_w3 = None
_account = None
_contract = None

# Polygon Amoy Testnet config
AMOY_RPC_URL = "https://rpc-amoy.polygon.technology"

# Contract address (fill in after deploying EvidenceRegistry.sol via Remix)
CONTRACT_ADDRESS = os.getenv("POLYGON_CONTRACT_ADDRESS", "")

# Minimal ABI — only the functions we need
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "caseId",     "type": "string"},
            {"internalType": "string", "name": "docName",    "type": "string"},
            {"internalType": "string", "name": "sha256Hash", "type": "string"}
        ],
        "name": "logEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "sha256Hash", "type": "string"}],
        "name": "verifyEvidence",
        "outputs": [
            {"internalType": "bool",   "name": "found",     "type": "bool"},
            {"internalType": "string", "name": "caseId",    "type": "string"},
            {"internalType": "string", "name": "docName",   "type": "string"},
            {"internalType": "uint256","name": "timestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

try:
    from web3 import Web3

    _private_key = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
    if not _private_key:
        print("[Blockchain] POLYGON_PRIVATE_KEY not set in .env — blockchain logging disabled")
    elif not CONTRACT_ADDRESS:
        print("[Blockchain] POLYGON_CONTRACT_ADDRESS not set in .env — deploy the contract first")
    else:
        _w3 = Web3(Web3.HTTPProvider(AMOY_RPC_URL))
        if _w3.is_connected():
            _account = _w3.eth.account.from_key(_private_key)
            _contract = _w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=CONTRACT_ABI
            )
            BLOCKCHAIN_AVAILABLE = True
            print(f"[Blockchain] Connected to Polygon Amoy. Wallet: {_account.address}")
        else:
            print("[Blockchain] Could not connect to Polygon Amoy RPC — check internet connection")
except Exception as e:
    print(f"[Blockchain] Init failed: {e}")


def log_hash_to_blockchain(case_id: str, doc_name: str, sha256_hash: str) -> dict:
    """
    Permanently logs the SHA-256 hash of an evidence document to Polygon blockchain.
    Returns a dict with tx_hash and polygonscan URL, or an error message.
    """
    if not BLOCKCHAIN_AVAILABLE:
        return {"status": "skipped", "reason": "Blockchain not configured"}

    try:
        nonce = _w3.eth.get_transaction_count(_account.address)
        gas_price = _w3.eth.gas_price

        # Build the transaction calling logEvidence()
        txn = _contract.functions.logEvidence(
            str(case_id), str(doc_name), str(sha256_hash)
        ).build_transaction({
            "chainId": 80002,        # Polygon Amoy chain ID
            "from":    _account.address,
            "nonce":   nonce,
            "gasPrice": gas_price,
            "gas":     200000,
        })

        signed = _w3.eth.account.sign_transaction(txn, private_key=_account.key)
        tx_hash = _w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hex = tx_hash.hex()

        polygonscan_url = f"https://amoy.polygonscan.com/tx/{tx_hex}"
        print(f"[Blockchain] Hash logged! TX: {polygonscan_url}")
        return {"status": "success", "tx_hash": tx_hex, "polygonscan_url": polygonscan_url}

    except Exception as e:
        print(f"[Blockchain] Transaction failed: {e}")
        return {"status": "error", "reason": str(e)}


def verify_hash_on_blockchain(sha256_hash: str) -> dict:
    """
    Queries the blockchain to verify if a hash was ever registered.
    Can be called without a private key — it is a read-only call.
    """
    if not BLOCKCHAIN_AVAILABLE:
        return {"status": "skipped", "reason": "Blockchain not configured"}
    try:
        found, case_id, doc_name, timestamp = _contract.functions.verifyEvidence(sha256_hash).call()
        if found:
            return {
                "status": "verified",
                "case_id": case_id,
                "doc_name": doc_name,
                "timestamp": timestamp,
                "polygonscan_url": f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"
            }
        return {"status": "not_found"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
