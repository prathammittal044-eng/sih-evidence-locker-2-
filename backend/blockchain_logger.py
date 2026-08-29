import hashlib
import os
from dotenv import load_dotenv

_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_backend_dir, ".env"))

BLOCKCHAIN_AVAILABLE = False
_w3 = None
_account = None
_contract = None

AMOY_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-amoy-bor-rpc.publicnode.com")
CONTRACT_ADDRESS = os.getenv("POLYGON_CONTRACT_ADDRESS", "")

# Ultra gas-optimized ABI — uint256 id + bytes32 hash only
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "_id", "type": "uint256"},
            {"internalType": "bytes32", "name": "_fileHash", "type": "bytes32"}
        ],
        "name": "logEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_id", "type": "uint256"},
            {"internalType": "bytes32", "name": "_fileHash", "type": "bytes32"}
        ],
        "name": "verifyEvidence",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "evidenceHashes",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    }
]

try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    _private_key = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
    if not _private_key:
        print("[Blockchain] POLYGON_PRIVATE_KEY not set - disabled")
    elif not CONTRACT_ADDRESS:
        print("[Blockchain] POLYGON_CONTRACT_ADDRESS not set - deploy first")
    else:
        _w3 = Web3(Web3.HTTPProvider(AMOY_RPC_URL))
        _w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if _w3.is_connected():
            _account = _w3.eth.account.from_key(_private_key)
            _contract = _w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=CONTRACT_ABI
            )
            BLOCKCHAIN_AVAILABLE = True
            print(f"[Blockchain] Connected. Wallet: {_account.address}")
        else:
            print("[Blockchain] Could not connect to Polygon RPC")
except Exception as e:
    print(f"[Blockchain] Init failed: {e}")


def _evidence_id_to_uint(evidence_id: str) -> int:
    """Convert string evidence ID to a deterministic uint256 using SHA-256."""
    return int.from_bytes(hashlib.sha256(evidence_id.encode()).digest(), 'big')


def _hex_to_bytes32(hex_str: str) -> bytes:
    """Convert a 64-char hex hash string to bytes32."""
    return bytes.fromhex(hex_str[:64])


def log_hash_to_blockchain(evidence_id: str, file_hash: str) -> dict:
    if not BLOCKCHAIN_AVAILABLE:
        return {"status": "skipped", "reason": "Blockchain not configured"}

    try:
        numeric_id = _evidence_id_to_uint(evidence_id)
        hash_bytes = _hex_to_bytes32(file_hash)

        nonce = _w3.eth.get_transaction_count(_account.address)
        gas_price = _w3.eth.gas_price

        fn = _contract.functions.logEvidence(numeric_id, hash_bytes)
        estimated_gas = fn.estimate_gas({"from": _account.address})
        gas_limit = int(estimated_gas * 1.3)

        txn = fn.build_transaction({
            "chainId": 80002,
            "from": _account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": gas_limit,
        })

        signed = _w3.eth.account.sign_transaction(txn, private_key=_account.key)
        tx_hash = _w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hex = tx_hash.hex()

        url = f"https://amoy.polygonscan.com/tx/0x{tx_hex}"
        print(f"[Blockchain] Evidence logged! TX: {url}")
        return {"status": "success", "tx_hash": tx_hex, "polygonscan_url": url}
    except Exception as e:
        print(f"[Blockchain] Transaction failed: {e}")
        return {"status": "error", "reason": str(e)}


def verify_hash_on_blockchain(evidence_id: str, file_hash: str) -> dict:
    if not BLOCKCHAIN_AVAILABLE:
        return {"status": "skipped", "reason": "Blockchain not configured"}

    try:
        numeric_id = _evidence_id_to_uint(evidence_id)
        hash_bytes = _hex_to_bytes32(file_hash)
        is_match = _contract.functions.verifyEvidence(numeric_id, hash_bytes).call()
        if is_match:
            return {
                "status": "verified",
                "polygonscan_url": f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"
            }
        stored = _contract.functions.evidenceHashes(numeric_id).call()
        if stored == b'\x00' * 32:
            return {"status": "not_found"}
        return {"status": "tampered"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
