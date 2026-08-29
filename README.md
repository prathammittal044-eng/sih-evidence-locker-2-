# 🔗 Blockchain-Based Digital Evidence Management System (SIH 2024)

An advanced, tamper-proof prototype for the secure storage and management of digital evidence (FIRs, forensics, court documents) leveraging **Polygon Blockchain**, **AI/NLP (Gemini + spaCy)**, and **OCR (Tesseract)**.

## 🚀 One-Click Setup (Windows)

For judges and evaluators running this on a Windows machine, we have provided a seamless one-click startup script.

1. **Double-click `start_windows.bat`** in the root directory.
2. The script will automatically:
   - Create an isolated Python Virtual Environment (`.venv`).
   - Install all required Backend Python packages.
   - Download the required AI NLP models.
   - Install all Frontend Node.js dependencies.
   - Launch two separate terminal windows for the Backend (Port 8000) and Frontend (Port 3000).
3. Open your browser and navigate to **http://localhost:3000**

### ⚠️ Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)
- **Tesseract-OCR:** Required for AI scanning of evidence PDFs. 
  - Install from: [UB-Mannheim Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - Ensure the install path is `C:\Program Files\Tesseract-OCR\tesseract.exe` (Default).

## 🛠 Tech Stack
- **Frontend:** Next.js 14, Tailwind CSS, Lucide React
- **Backend:** FastAPI, SQLite (Local Database), spaCy, Google Gemini Vision
- **Blockchain:** Polygon Amoy Testnet (Web3.py, Solidity)
- **AI/ML:** Tesseract OCR (Optical Character Recognition), NLP Semantic Search

## ⛓ Blockchain Integrity Architecture
This project does **not** store sensitive files (like FIR PDFs) on the public blockchain due to privacy and extreme gas costs. Instead, it utilizes **Cryptographic Hashing for Chain of Custody**:
1. When evidence is uploaded, the backend generates a **SHA-256 Hash** of the file.
2. Only this hash, along with the unique Case ID, is securely logged to our ultra-gas-optimized Smart Contract on the **Polygon Amoy Testnet**.
3. When verifying, the system checks the local file's hash against the immutable ledger. If even a single byte of the local file was tampered with, the system triggers a permanent alert.

*(Note: The current smart contract is optimized down to ~50k gas (approx 0.003 MATIC) per evidence log!)*
