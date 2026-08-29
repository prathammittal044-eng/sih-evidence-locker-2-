from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
import models, schemas
from database import engine, get_db
import hashlib
import threading
import blockchain_logger
import os
import uuid
import subprocess
from datetime import datetime, timezone

# Lazy-load vector search so startup doesn't block if chromadb isn't installed yet
try:
    import vector_search as vs
    VECTOR_SEARCH_ENABLED = True
    print("[VectorSearch] Semantic search engine loaded successfully.")
except Exception as e:
    VECTOR_SEARCH_ENABLED = False
    print(f"[VectorSearch] Not available: {e}")

# Load OCR engine
try:
    import ocr_engine as ocr
    OCR_ENABLED = ocr.OCR_AVAILABLE
    print(f"[OCR] Engine loaded. Tesseract available: {OCR_ENABLED}")
except Exception as e:
    OCR_ENABLED = False
    print(f"[OCR] Not available: {e}")

# --- Role definitions ---
ROLE_PERMISSIONS = {
    "Officer":  {"can_upload": True,  "can_seal": False, "can_verify": True},
    "Reviewer": {"can_upload": False, "can_seal": False, "can_verify": True},
    "Judge":    {"can_upload": False, "can_seal": True,  "can_verify": True},
}

# --- JWT Config ---
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib as _hashlib

SECRET_KEY  = "SIH2026-EVIDENCE-LOCKER-SECRET-XK9Z"
ALGORITHM   = "HS256"
TOKEN_HOURS = 8
bearer_scheme = HTTPBearer(auto_error=False)

def _hash_pw(pw: str) -> str:
    return _hashlib.sha256((pw + SECRET_KEY).encode()).hexdigest()

def _verify_pw(plain: str, hashed: str) -> bool:
    return _hash_pw(plain) == hashed

USERS_STATIC = {
    1: {
        "name": "Sub-Inspector Sharma", "role": "Officer",
        "badge": "9482A", "username": "sharma",
        "hashed_password": _hash_pw("Officer@123"),
        "department": "Cyber Crime Unit, Delhi Police",
    },
    2: {
        "name": "Chief Inspector Verma", "role": "Reviewer",
        "badge": "1109X", "username": "verma",
        "hashed_password": _hash_pw("Reviewer@123"),
        "department": "Special Investigation Branch",
    },
    3: {
        "name": "Hon. Judge Patel", "role": "Judge",
        "badge": "JDG-01", "username": "judge1",
        "hashed_password": _hash_pw("Judge@123"),
        "department": "Sessions Court, District Court",
    },
}

def get_user_info(user_id: int) -> dict:
    u = USERS_STATIC.get(user_id, {})
    return {
        "name": u.get("name", "Unknown"), "role": u.get("role", "Unknown"),
        "badge": u.get("badge", "N/A"), "department": u.get("department", "")
    }

def get_user_role(user_id: int) -> str:
    return get_user_info(user_id)["role"]

def create_access_token(user_id: int) -> str:
    from datetime import timedelta
    u = USERS_STATIC[user_id]
    payload = {
        "sub": str(user_id),
        "name": u["name"], "role": u["role"],
        "badge": u["badge"], "department": u["department"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return {}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")
    return {"id": int(payload["sub"]), "name": payload["name"],
            "role": payload["role"], "badge": payload["badge"]}


# -------------------------------------------------------
# Run migrations for new columns (safe to call every start)
# -------------------------------------------------------
def run_migrations():
    from sqlalchemy import text
    from database import engine as _engine
    with _engine.connect() as conn:
        for col, typedef in [
            ("is_sealed", "BOOLEAN DEFAULT 0"),
            ("sealed_by",  "INTEGER"),
            ("sealed_at",  "DATETIME"),
            ("extracted_text", "TEXT"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE cases ADD COLUMN {col} {typedef}"))
                conn.commit()
            except Exception:
                pass
        try:
            conn.execute(text("ALTER TABLE document_versions ADD COLUMN extracted_text TEXT"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE document_versions ADD COLUMN ai_summary TEXT"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE document_versions ADD COLUMN entities TEXT"))
            conn.commit()
        except Exception:
            pass
        # New: document images table (create via metadata if not exists)
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS document_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_version_id INTEGER REFERENCES document_versions(id),
                    image_path TEXT NOT NULL,
                    page_number INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        except Exception:
            pass

run_migrations()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Evidence Locker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------------
# Text Extraction Helper (with OCR for images and scanned PDFs)
# -------------------------------------------------------
def extract_text(file_content: bytes, filename: str) -> str:
    """Extract text from a file. Uses OCR for images and scanned PDFs."""
    ext = filename.lower().split('.')[-1]

    if ext == 'txt':
        try:
            return file_content.decode('utf-8')
        except:
            return ""

    elif ext == 'pdf':
        # Use OCR engine for full PDF processing (text + images + scanned pages)
        if OCR_ENABLED:
            text, _ = ocr.process_pdf(file_content, 0, UPLOAD_DIR)
            if text.strip():
                return text
        # Fallback: plain pypdf text extraction
        try:
            import pypdf, io as _io
            pdf = pypdf.PdfReader(_io.BytesIO(file_content))
            return "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return ""

    elif OCR_ENABLED and ocr.is_image_file(filename):
        # Direct OCR on image files (JPG, PNG, etc.)
        return ocr.ocr_image_file(file_content)

    return ""


def extract_and_save_images(file_content: bytes, filename: str, db_version_id: int, db: any) -> list:
    """
    After a document is saved, extract embedded images and store them in DocumentImage table.
    Returns list of saved image filenames.
    """
    if not OCR_ENABLED:
        return []

    saved = []
    ext = filename.lower().split('.')[-1]

    if ext == 'pdf':
        _, image_filenames = ocr.process_pdf(file_content, db_version_id, UPLOAD_DIR)
        for img_file in image_filenames:
            db_img = models.DocumentImage(
                document_version_id=db_version_id,
                image_path=img_file,
            )
            db.add(db_img)
            saved.append(img_file)

    elif ocr.is_image_file(filename):
        # The uploaded file itself IS the image — save a reference directly
        img_filename = f"docv{db_version_id}_original.{ext}"
        img_path = os.path.join(UPLOAD_DIR, img_filename)
        with open(img_path, 'wb') as f:
            f.write(file_content)
        db_img = models.DocumentImage(
            document_version_id=db_version_id,
            image_path=img_filename,
        )
        db.add(db_img)
        saved.append(img_filename)

    if saved:
        db.commit()

    return saved

# -------------------------------------------------------
# Auth Endpoints — Login & Me
# -------------------------------------------------------
@app.post("/auth/login/")
def login(username: str = Form(...), password: str = Form(...)):
    """Authenticate user and return a JWT token."""
    # Find user by username
    matched_id = None
    for uid, u in USERS_STATIC.items():
        if u["username"] == username.strip().lower():
            matched_id = uid
            break

    if matched_id is None or not _verify_pw(password, USERS_STATIC[matched_id]["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(matched_id)
    u = USERS_STATIC[matched_id]
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": matched_id,
            "name": u["name"],
            "role": u["role"],
            "badge": u["badge"],
            "department": u["department"],
        }
    }

@app.get("/auth/me/")
def get_me(current_user: dict = Depends(get_current_user)):
    """Return current authenticated user's info."""
    return current_user

# -------------------------------------------------------
# File serving
# -------------------------------------------------------
@app.get("/files/{file_path}")
def get_file(file_path: str, user_id: int = None, document_id: int = None, db: Session = Depends(get_db)):
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    if user_id and document_id:
        u = get_user_info(user_id)
        audit = models.AuditLog(user_id=user_id, action="VIEW_FILE",
            details=f"{u['name']} ({u['role']}, Badge {u['badge']}) viewed document {document_id} (file: {file_path})")
        db.add(audit)
        db.commit()
    return FileResponse(full_path)

# -------------------------------------------------------
# Audit logs
# -------------------------------------------------------
@app.get("/audit-logs/", response_model=list[schemas.AuditLog])
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(100).all()

@app.get("/")
def read_root():
    return {"message": "Welcome to Digital Evidence Locker API"}

# -------------------------------------------------------
# Dummy data setup
# -------------------------------------------------------
@app.post("/setup-dummy-data/")
def setup_dummy_data(db: Session = Depends(get_db)):
    if db.query(models.User).first():
        return {"message": "Dummy data already exists"}
    officer  = models.User(username="sharma",  role="Officer")
    reviewer = models.User(username="verma",   role="Reviewer")
    judge    = models.User(username="judge1",  role="Judge")
    db.add_all([officer, reviewer, judge])
    case1 = models.Case(case_number="FIR-2026-104", title="Theft at Downtown")
    db.add(case1)
    db.commit()
    return {"message": "Dummy data created"}

# -------------------------------------------------------
# Case Management
# -------------------------------------------------------
@app.post("/cases/", response_model=schemas.Case)
def create_case(case: schemas.CaseCreate, db: Session = Depends(get_db)):
    db_case = models.Case(**case.model_dump())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@app.get("/cases/", response_model=list[schemas.Case])
def get_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Case).offset(skip).limit(limit).all()

@app.get("/cases/{case_id}", response_model=schemas.Case)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

# -------------------------------------------------------
# Feature 2: Case Sealing (Judge only)
# -------------------------------------------------------
@app.post("/cases/{case_id}/seal/")
def seal_case(case_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    role = get_user_role(user_id)
    if role != "Judge":
        raise HTTPException(status_code=403, detail=f"Access Denied: Only a Judge can seal a case. Your role is '{role}'.")
    
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.is_sealed:
        raise HTTPException(status_code=400, detail="Case is already sealed.")
    
    case.is_sealed = True
    case.sealed_by = user_id
    case.sealed_at = datetime.now(timezone.utc)
    case.status = "Sealed"
    
    u = get_user_info(user_id)
    audit = models.AuditLog(user_id=user_id, action="SEAL_CASE",
        details=f"CASE SEALED by {u['name']} ({u['role']}, Badge {u['badge']}) — Case #{case.case_number} is now permanently sealed for trial.")
    db.add(audit)
    db.commit()
    return {"message": f"Case {case.case_number} has been permanently sealed by {u['name']}."}

# -------------------------------------------------------
# Feature 3: Chain of Custody Report
# -------------------------------------------------------
@app.get("/cases/{case_id}/report/")
def download_report(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "=" * 70,
        "        OFFICIAL CHAIN OF CUSTODY REPORT",
        "        Digital Evidence Locker — SIH Prototype",
        "=" * 70,
        f"  Generated At : {now}",
        f"  Case Number  : {case.case_number}",
        f"  Case Title   : {case.title}",
        f"  Status       : {case.status}",
    ]
    if case.is_sealed and case.sealed_at:
        sealer = get_user_info(case.sealed_by or 0)
        lines.append(f"  Sealed By    : {sealer['name']} ({sealer['role']}, Badge {sealer['badge']})")
        lines.append(f"  Sealed At    : {case.sealed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines += ["=" * 70, ""]

    docs = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    if not docs:
        lines.append("  No documents found in this case.")
    else:
        lines.append(f"  DOCUMENTS ({len(docs)} total)")
        lines.append("-" * 70)
        for doc in docs:
            lines += [
                f"",
                f"  Document   : {doc.name}",
                f"  Type       : {doc.doc_type}",
                f"  Created    : {doc.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"  Internal ID: #{doc.id}",
                f"  Versions   : {len(doc.versions)}",
            ]
            for v in sorted(doc.versions, key=lambda x: x.version_number):
                u = get_user_info(v.uploaded_by)
                lines += [
                    f"",
                    f"    ┌─ Version v{v.version_number}.0  [{v.status}]",
                    f"    │  Uploaded By : {u['name']}",
                    f"    │  Role        : {u['role']}",
                    f"    │  Badge No.   : {u['badge']}",
                    f"    │  Timestamp   : {v.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    f"    └─ SHA-256     : {v.file_hash}",
                ]
            lines.append("-" * 70)

    lines += ["", "  AUDIT TRAIL (last 50 entries for this report)", "-" * 70]
    audit_logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.asc()).limit(50).all()
    for log in audit_logs:
        u = get_user_info(log.user_id)
        lines.append(f"  [{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]  {log.action:<20} — {log.details}")
    
    lines += ["", "=" * 70,
              "  This report is an official record of the chain of custody.",
              "  Any alteration to this document may constitute evidence tampering.",
              "=" * 70]
    
    report_text = "\n".join(lines)
    filename = f"ChainOfCustody_{case.case_number}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    return PlainTextResponse(
        content=report_text,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# -------------------------------------------------------
# Document Upload (with RBAC + Sealed-case check)
# -------------------------------------------------------
@app.post("/cases/{case_id}/documents/")
def upload_document(
    case_id: int,
    name: str = Form(...),
    doc_type: str = Form(...),
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # --- RBAC Check ---
    role = get_user_role(user_id)
    if not ROLE_PERMISSIONS.get(role, {}).get("can_upload", False):
        raise HTTPException(status_code=403,
            detail=f"Access Denied: Your role '{role}' does not have permission to upload documents. Only Officers can upload.")
    
    # --- Sealed Case Check ---
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.is_sealed:
        raise HTTPException(status_code=403,
            detail="This case has been permanently sealed by a Judge. No new documents can be added.")

    file_content = file.file.read()
    object_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, object_name)
    extracted_text = extract_text(file_content, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    try:
        subprocess.run(['attrib', '+r', file_path], shell=True)
    except Exception as e:
        print(f"Failed to lock file {file_path}: {e}")

    db_doc = models.Document(case_id=case_id, name=name, doc_type=doc_type)
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # --- Unique hash per version: SHA-256(file_content + case_id + doc_id + version) ---
    # This ensures that v1 and v2 of the same file get DIFFERENT hashes,
    # and the same file in two different cases also gets DIFFERENT hashes.
    version_number = 1
    hash_salt = f"|case:{case_id}|doc:{db_doc.id}|version:{version_number}".encode()
    file_hash = hashlib.sha256(file_content + hash_salt).hexdigest()

    db_version = models.DocumentVersion(
        document_id=db_doc.id, version_number=version_number,
        file_path=object_name, file_hash=file_hash,
        status="Active", uploaded_by=user_id,
        extracted_text=extracted_text,
        ai_summary="",
        entities="{}"
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)

    # --- OCR Image Extraction (must happen BEFORE NLP so Gemini Vision can see images) ---
    saved_image_names = extract_and_save_images(file_content, file.filename, db_version.id, db)
    image_paths = [os.path.join(UPLOAD_DIR, img) for img in (saved_image_names or [])]

    # --- AI NLP Insights (Summary + Entities + Clean Text) ---
    ai_summary = ""
    entities_json = "{}"
    try:
        import nlp_engine
        import json
        nlp_data = nlp_engine.analyze_document(extracted_text, image_paths=image_paths)
        ai_summary = nlp_data.get("summary", "")
        entities_json = json.dumps(nlp_data.get("entities", {}))
        
        # Override the messy Tesseract text with Gemini's perfect transcription if available
        if "full_text" in nlp_data and nlp_data["full_text"]:
            extracted_text = nlp_data["full_text"]
    except Exception as e:
        print(f"NLP Engine skipped: {e}")

    # Save NLP results back to the version
    db_version.extracted_text = extracted_text
    db_version.ai_summary = ai_summary
    db_version.entities = entities_json
    db.commit()

    u = get_user_info(user_id)
    audit = models.AuditLog(user_id=user_id, action="UPLOAD_DOCUMENT",
        details=f"{u['name']} ({u['role']}, Badge {u['badge']}) uploaded '{name}' ({doc_type}) to Case #{case.case_number}")
    db.add(audit)
    db.commit()

    # --- Vector Index ---
    if VECTOR_SEARCH_ENABLED and extracted_text:
        vs.add_document_to_index(
            doc_id=f"version_{db_version.id}",
            case_id=case_id,
            doc_name=name,
            doc_type=doc_type,
            text=extracted_text
        )


    # --- Blockchain Logging ---
    try:
        evidence_id = f"case_{case_id}_doc_{db_doc.id}_v{version_number}"
        threading.Thread(target=blockchain_logger.log_hash_to_blockchain, args=(evidence_id, file_hash), daemon=True).start()
    except Exception as e:
        print(f"Blockchain logging failed: {e}")

    return {"message": "Document uploaded securely", "document_id": db_doc.id, "hash": file_hash}

# -------------------------------------------------------
# Document Version Update (with RBAC + Sealed-case check)
# -------------------------------------------------------
@app.post("/documents/{document_id}/versions/")
def update_document(
    document_id: int,
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # --- RBAC Check ---
    role = get_user_role(user_id)
    if not ROLE_PERMISSIONS.get(role, {}).get("can_upload", False):
        raise HTTPException(status_code=403,
            detail=f"Access Denied: Your role '{role}' cannot update document versions. Only Officers can do this.")

    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # --- Sealed Case Check ---
    case = db.query(models.Case).filter(models.Case.id == doc.case_id).first()
    if case and case.is_sealed:
        raise HTTPException(status_code=403,
            detail="This case has been permanently sealed. No new versions can be created.")

    latest_version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id
    ).order_by(models.DocumentVersion.version_number.desc()).first()

    if latest_version:
        latest_version.status = "Superseded"
        new_version_num = latest_version.version_number + 1
    else:
        new_version_num = 1

    file_content = file.file.read()
    # --- Unique hash per version: SHA-256(file_content + doc_id + version) ---
    hash_salt = f"|case:{doc.case_id}|doc:{document_id}|version:{new_version_num}".encode()
    file_hash = hashlib.sha256(file_content + hash_salt).hexdigest()
    object_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, object_name)

    # Step 1: Save file to disk first (Gemini needs the physical file path)
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    try:
        subprocess.run(['attrib', '+r', file_path], shell=True)
    except Exception as e:
        print(f"Failed to lock file {file_path}: {e}")

    # Step 2: Tesseract fallback text (used only if Gemini is unavailable)
    extracted_text = extract_text(file_content, file.filename)

    # Step 3: Save a temporary DB record so we can extract images with proper version ID
    new_version = models.DocumentVersion(
        document_id=document_id, version_number=new_version_num,
        file_path=object_name, file_hash=file_hash,
        status="Active", uploaded_by=user_id,
        extracted_text=extracted_text,
        ai_summary="",
        entities="{}"
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    # Step 4: Extract images (Gemini Vision needs the image file paths)
    extract_and_save_images(file_content, file.filename, new_version.id, db)

    # Step 5: Collect image paths and send to Gemini Vision (same as initial upload)
    import json
    ai_summary = ""
    entities_json = "{}"
    try:
        import nlp_engine
        image_records = db.query(models.DocumentImage).filter(
            models.DocumentImage.document_version_id == new_version.id
        ).all()
        image_paths = [os.path.join(UPLOAD_DIR, img.image_path) for img in image_records]

        if image_paths:
            # Gemini Vision analyzes the actual images — no garbled Tesseract text!
            nlp_data = nlp_engine.analyze_document(extracted_text, image_paths=image_paths)
        else:
            nlp_data = nlp_engine.analyze_document(extracted_text)

        # Overwrite extracted_text with Gemini's perfect full_text
        gemini_full_text = nlp_data.get("full_text", "")
        if gemini_full_text:
            extracted_text = gemini_full_text

        ai_summary = nlp_data.get("summary", "")
        entities_json = json.dumps(nlp_data.get("entities", {}))
    except Exception as e:
        print(f"NLP Engine skipped: {e}")

    # Step 6: Update the DB record with the final Gemini-analysed text
    new_version.extracted_text = extracted_text
    new_version.ai_summary = ai_summary
    new_version.entities = entities_json

    u = get_user_info(user_id)
    audit = models.AuditLog(user_id=user_id, action="CREATE_VERSION",
        details=f"{u['name']} ({u['role']}, Badge {u['badge']}) updated document '{doc.name}' to v{new_version_num}")
    db.add(audit)
    db.commit()

    # --- Vector Index ---
    if VECTOR_SEARCH_ENABLED and extracted_text:
        vs.add_document_to_index(
            doc_id=f"version_{new_version.id}",
            case_id=doc.case_id,
            doc_name=doc.name,
            doc_type=doc.doc_type,
            text=extracted_text
        )


    # --- Blockchain Logging ---
    try:
        evidence_id = f"case_{doc.case_id}_doc_{document_id}_v{new_version_num}"
        threading.Thread(target=blockchain_logger.log_hash_to_blockchain, args=(evidence_id, file_hash), daemon=True).start()
    except Exception as e:
        print(f"Blockchain logging failed: {e}")

    return {"message": f"Document updated to version {new_version_num}", "hash": file_hash}

# -------------------------------------------------------
# Integrity Verification
# -------------------------------------------------------
@app.get("/documents/{document_id}/verify/")
def verify_document_integrity(document_id: int, db: Session = Depends(get_db)):
    versions = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == document_id).all()
    if not versions:
        raise HTTPException(status_code=404, detail="No versions found")

    # Look up the document to get case_id for the salt
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    case_id = doc.case_id if doc else 0

    results = []
    for v in versions:
        try:
            full_path = os.path.join(UPLOAD_DIR, v.file_path)
            if not os.path.exists(full_path):
                results.append({"version": v.version_number, "status": "MISSING", "message": "File was deleted from the server!"})
                continue
            with open(full_path, "rb") as f:
                file_bytes = f.read()

            # Recompute using the SAME salted formula used at upload time
            hash_salt = f"|case:{case_id}|doc:{document_id}|version:{v.version_number}".encode()
            current_hash = hashlib.sha256(file_bytes + hash_salt).hexdigest()

            if current_hash == v.file_hash:
                message = "Cryptographic hash matches Local DB."
                try:
                    evidence_id = f"case_{case_id}_doc_{document_id}_v{v.version_number}"
                    bc_result = blockchain_logger.verify_hash_on_blockchain(evidence_id, current_hash)
                    if bc_result.get("status") == "verified":
                        message = "VERIFIED BY POLYGON BLOCKCHAIN. Cryptographic hash perfectly matches the immutable ledger."
                    elif bc_result.get("status") == "tampered":
                        results.append({"version": v.version_number, "status": "TAMPERED", "message": "ALERT: Hash does not match the Blockchain Ledger!"})
                        continue
                except Exception as e:
                    pass

                results.append({"version": v.version_number, "status": "VERIFIED",
                                 "message": message})

            else:
                results.append({"version": v.version_number, "status": "TAMPERED",
                                 "message": "ALERT: File content does not match the original hash!"})
        except Exception as e:
            results.append({"version": v.version_number, "status": "ERROR", "message": f"Could not read file: {str(e)}"})
    return {"document_id": document_id, "integrity_checks": results}

# -------------------------------------------------------
# OCR: Get extracted images for a document version
# -------------------------------------------------------
@app.get("/versions/{version_id}/images/")
def get_version_images(version_id: int, db: Session = Depends(get_db)):
    """Return all images extracted from a specific document version."""
    images = db.query(models.DocumentImage).filter(
        models.DocumentImage.document_version_id == version_id
    ).all()
    return [
        {
            "id": img.id,
            "image_path": img.image_path,
            "url": f"/files/{img.image_path}",
            "page_number": img.page_number,
        }
        for img in images
    ]

@app.get("/ocr/status/")
def get_ocr_status():
    """Return OCR engine availability status."""
    return {
        "enabled": OCR_ENABLED,
        "engine": "Tesseract OCR" if OCR_ENABLED else "Not available",
        "message": "OCR scanning active — images and scanned PDFs will be processed." if OCR_ENABLED else "Install Tesseract OCR to enable scanning."
    }

# -------------------------------------------------------
# True Semantic AI Search (Vector Embeddings via ChromaDB)
# -------------------------------------------------------
@app.get("/search/")
def search_inside_files(q: str, db: Session = Depends(get_db)):
    if not q or not q.strip():
        return []

    # --- Path 1: Semantic Vector Search (if ChromaDB is available) ---
    if VECTOR_SEARCH_ENABLED:
        try:
            results = vs.semantic_search(q, n_results=20)
            if results:
                # Deduplicate case IDs while preserving relevance order
                seen = []
                for r in results:
                    cid = r["case_id"]
                    if cid not in seen:
                        seen.append(cid)
                return seen
        except Exception as e:
            print(f"[VectorSearch] Semantic search failed, falling back: {e}")

    # --- Path 2: Keyword Fallback (if ChromaDB not available) ---
    STOP_WORDS = {"i","me","my","we","our","you","your","he","him","his","she","her","it","its","they","them","their","what","which","who","whom","this","that","these","those","am","is","are","was","were","be","been","being","have","has","had","do","does","did","a","an","the","and","but","if","or","because","as","until","while","of","at","by","for","with","about","against","between","into","through","during","before","after","above","below","to","from","up","down","in","out","on","off","over","under","again","further","then","once","here","there","when","where","why","how","all","any","both","each","few","more","most","other","some","such","no","nor","not","only","own","same","so","than","too","very","s","t","can","will","just","don","should","now","find","case","cases","around","people","months","years","days","show","me","looking","search"}
    words = ''.join(c if c.isalnum() else ' ' for c in q.lower()).split()
    keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    if not keywords:
        return []
    versions = db.query(models.DocumentVersion).filter(models.DocumentVersion.extracted_text.isnot(None)).all()
    case_scores = {}
    for v in versions:
        if not v.document or not v.document.case_id:
            continue
        text = v.extracted_text.lower()
        score = sum(text.count(kw) for kw in keywords)
        if score > 0:
            cid = v.document.case_id
            case_scores[cid] = case_scores.get(cid, 0) + score
    return sorted(case_scores.keys(), key=lambda k: case_scores[k], reverse=True)

# -------------------------------------------------------
# Vector Search Status + Backfill Endpoint
# -------------------------------------------------------
@app.get("/search/status/")
def get_search_status():
    if not VECTOR_SEARCH_ENABLED:
        return {"enabled": False, "indexed_documents": 0, "message": "ChromaDB not installed"}
    return {
        "enabled": True,
        "indexed_documents": vs.get_indexed_count(),
        "message": "Semantic vector search is active"
    }

@app.post("/search/backfill/")
def backfill_vector_index(db: Session = Depends(get_db)):
    """Backfill the vector index for all existing documents with extracted text."""
    if not VECTOR_SEARCH_ENABLED:
        raise HTTPException(status_code=503, detail="Vector search engine not available")
    versions = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.extracted_text.isnot(None)
    ).all()
    count = 0
    for v in versions:
        if v.document and v.extracted_text and v.extracted_text.strip():
            vs.add_document_to_index(
                doc_id=f"version_{v.id}",
                case_id=v.document.case_id,
                doc_name=v.document.name,
                doc_type=v.document.doc_type,
                text=v.extracted_text
            )
            count += 1
    return {"message": f"Successfully indexed {count} documents into semantic vector database."}
