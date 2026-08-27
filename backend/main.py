from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
import models, schemas
from database import engine, get_db
import hashlib
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

# --- Role definitions ---
ROLE_PERMISSIONS = {
    "Officer":  {"can_upload": True,  "can_seal": False, "can_verify": True},
    "Reviewer": {"can_upload": False, "can_seal": False, "can_verify": True},
    "Judge":    {"can_upload": False, "can_seal": True,  "can_verify": True},
}

USERS_STATIC = {
    1: {"name": "Sub-Inspector Sharma", "role": "Officer",  "badge": "9482A"},
    2: {"name": "Chief Inspector Verma", "role": "Reviewer", "badge": "1109X"},
    3: {"name": "Hon. Judge Patel",      "role": "Judge",    "badge": "JDG-01"},
}

def get_user_info(user_id: int) -> dict:
    return USERS_STATIC.get(user_id, {"name": "Unknown", "role": "Unknown", "badge": "N/A"})

def get_user_role(user_id: int) -> str:
    return get_user_info(user_id)["role"]

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

run_migrations()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Evidence Locker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------------
# Text Extraction Helper
# -------------------------------------------------------
def extract_text(file_content: bytes, filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    if ext == 'txt':
        try:
            return file_content.decode('utf-8')
        except:
            return ""
    elif ext == 'pdf':
        try:
            import pypdf
            import io
            pdf = pypdf.PdfReader(io.BytesIO(file_content))
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return ""
    return ""

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
    file_hash = hashlib.sha256(file_content).hexdigest()
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

    db_version = models.DocumentVersion(
        document_id=db_doc.id, version_number=1,
        file_path=object_name, file_hash=file_hash,
        status="Active", uploaded_by=user_id,
        extracted_text=extracted_text
    )
    db.add(db_version)

    u = get_user_info(user_id)
    audit = models.AuditLog(user_id=user_id, action="UPLOAD_DOCUMENT",
        details=f"{u['name']} ({u['role']}, Badge {u['badge']}) uploaded '{name}' ({doc_type}) to Case #{case.case_number}")
    db.add(audit)
    db.commit()
    db.refresh(db_version)

    # --- Vector Index ---
    if VECTOR_SEARCH_ENABLED and extracted_text:
        vs.add_document_to_index(
            doc_id=f"version_{db_version.id}",
            case_id=case_id,
            doc_name=name,
            doc_type=doc_type,
            text=extracted_text
        )

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
    file_hash = hashlib.sha256(file_content).hexdigest()
    object_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, object_name)
    extracted_text = extract_text(file_content, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    try:
        subprocess.run(['attrib', '+r', file_path], shell=True)
    except Exception as e:
        print(f"Failed to lock file {file_path}: {e}")

    new_version = models.DocumentVersion(
        document_id=document_id, version_number=new_version_num,
        file_path=object_name, file_hash=file_hash,
        status="Active", uploaded_by=user_id,
        extracted_text=extracted_text
    )
    db.add(new_version)

    u = get_user_info(user_id)
    audit = models.AuditLog(user_id=user_id, action="CREATE_VERSION",
        details=f"{u['name']} ({u['role']}, Badge {u['badge']}) updated document '{doc.name}' to v{new_version_num}")
    db.add(audit)
    db.commit()
    db.refresh(new_version)

    # --- Vector Index ---
    if VECTOR_SEARCH_ENABLED and extracted_text:
        vs.add_document_to_index(
            doc_id=f"version_{new_version.id}",
            case_id=doc.case_id,
            doc_name=doc.name,
            doc_type=doc.doc_type,
            text=extracted_text
        )

    return {"message": f"Document updated to version {new_version_num}", "hash": file_hash}

# -------------------------------------------------------
# Integrity Verification
# -------------------------------------------------------
@app.get("/documents/{document_id}/verify/")
def verify_document_integrity(document_id: int, db: Session = Depends(get_db)):
    versions = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == document_id).all()
    if not versions:
        raise HTTPException(status_code=404, detail="No versions found")
    results = []
    for v in versions:
        try:
            full_path = os.path.join(UPLOAD_DIR, v.file_path)
            if not os.path.exists(full_path):
                results.append({"version": v.version_number, "status": "MISSING", "message": "File was deleted from the server!"})
                continue
            with open(full_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            if current_hash == v.file_hash:
                results.append({"version": v.version_number, "status": "VERIFIED", "message": "Cryptographic hash matches. File is intact."})
            else:
                results.append({"version": v.version_number, "status": "TAMPERED", "message": "ALERT: File content does not match the original hash!"})
        except Exception as e:
            results.append({"version": v.version_number, "status": "ERROR", "message": f"Could not read file: {str(e)}"})
    return {"document_id": document_id, "integrity_checks": results}

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
