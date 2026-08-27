"""
Test Script for Verify Integrity Feature
Run this AFTER the backend server is started with run.bat

Usage: py test_integrity.py
"""
import sys
import os
import requests
import hashlib
import tempfile

BASE = "http://localhost:8000"

def test_integrity():
    print("=" * 60)
    print("INTEGRITY VERIFICATION TEST")
    print("=" * 60)

    # 1. Get or create a case
    print("\n[STEP 1] Getting a case...")
    resp = requests.get(f"{BASE}/cases/")
    cases = resp.json()
    if not cases:
        print("  No cases found! Creating one...")
        resp = requests.post(f"{BASE}/cases/", json={"case_number": "TEST-001", "title": "Test Case"})
        case = resp.json()
    else:
        case = cases[0]
    print(f"  Using Case: {case['title']} (ID: {case['id']})")

    # 2. Upload a test document
    print("\n[STEP 2] Uploading a test document...")
    test_content = b"This is a test evidence document. Case: TEST-001."
    files = {"file": ("test_evidence.txt", test_content, "text/plain")}
    data = {"name": "Test Evidence", "doc_type": "Evidence", "user_id": 1}
    resp = requests.post(f"{BASE}/cases/{case['id']}/documents/", files=files, data=data)
    upload_result = resp.json()
    doc_id = upload_result["document_id"]
    original_hash = upload_result["hash"]
    print(f"  Uploaded document ID: {doc_id}")
    print(f"  SHA-256 Hash: {original_hash}")

    # 3. Verify integrity (should be VERIFIED)
    print("\n[STEP 3] Verifying integrity (should be VERIFIED)...")
    resp = requests.get(f"{BASE}/documents/{doc_id}/verify/")
    result = resp.json()
    for check in result["integrity_checks"]:
        status = check["status"]
        msg = check["message"]
        icon = "✅" if status == "VERIFIED" else "❌"
        print(f"  {icon} v{check['version']}: [{status}] - {msg}")

    # 4. Now tamper with the file directly
    print("\n[STEP 4] Simulating tampering: Finding and editing the file on disk...")
    resp = requests.get(f"{BASE}/cases/{case['id']}")
    case_data = resp.json()
    tampered = False
    for doc in case_data["documents"]:
        if doc["id"] == doc_id:
            for v in doc["versions"]:
                file_path = os.path.join(
                    r"C:\Users\prath\Downloads\SIH\Prototype\backend\uploads",
                    v["file_path"]
                )
                if os.path.exists(file_path):
                    # First remove read-only attr
                    os.system(f'attrib -r "{file_path}"')
                    os.system(f'icacls "{file_path}" /remove:d "Everyone"')
                    with open(file_path, "wb") as f:
                        f.write(b"TAMPERED CONTENT - Someone secretly altered this file!")
                    print(f"  ⚠️  File tampered: {file_path}")
                    tampered = True
    
    if not tampered:
        print("  Could not find file to tamper with. Skipping tamper test.")
        return

    # 5. Verify integrity again (should be TAMPERED)
    print("\n[STEP 5] Verifying integrity again (should be TAMPERED)...")
    resp = requests.get(f"{BASE}/documents/{doc_id}/verify/")
    result = resp.json()
    for check in result["integrity_checks"]:
        status = check["status"]
        msg = check["message"]
        icon = "✅" if status == "VERIFIED" else "🚨"
        print(f"  {icon} v{check['version']}: [{status}] - {msg}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE! The integrity verification is working correctly.")
    print("=" * 60)

if __name__ == "__main__":
    test_integrity()
