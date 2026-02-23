"""
main.py
=======
FastAPI application for Lok Sabha Database
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
from dotenv import load_dotenv

from database import get_db, test_connection
from models import *

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title=os.getenv('API_TITLE', 'Lok Sabha Database API'),
    description=os.getenv('API_DESCRIPTION', 'REST API for Lok Sabha member data'),
    version=os.getenv('API_VERSION', '1.0.0'),
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# HEALTH CHECK & ROOT
# ============================================================

@app.get("/", tags=["Root"])
def root():
    """API root endpoint"""
    return {
        "message": "Lok Sabha Database API",
        "version": os.getenv('API_VERSION', '1.0.0'),
        "documentation": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Check API and database health"""
    db_status = "connected" if test_connection() else "disconnected"
    status = "healthy" if db_status == "connected" else "unhealthy"
    
    return {
        "status": status,
        "database": db_status,
        "message": "API is running" if status == "healthy" else "Database connection failed"
    }

# ============================================================
# MEMBERS
# ============================================================

@app.get("/api/members", response_model=PaginatedResponse, tags=["Members"])
def get_members(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    party: Optional[str] = Query(None, description="Filter by party name"),
    state: Optional[str] = Query(None, description="Filter by state"),
    loksabha: Optional[int] = Query(None, description="Filter by Lok Sabha term"),
    db = Depends(get_db)
):
    """Get all members with pagination and filters"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = []
    params = []
    
    if party:
        where_clauses.append("party LIKE %s")
        params.append(f"%{party}%")
    if state:
        where_clauses.append("state LIKE %s")
        params.append(f"%{state}%")
    if loksabha:
        where_clauses.append("terms LIKE %s")
        params.append(f"%{loksabha}%")
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    offset = (page - 1) * size
    
    # Get total count
    cursor.execute(f"SELECT COUNT(*) as total FROM lok_sabha_members WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    # Get data
    cursor.execute(
        f"SELECT * FROM lok_sabha_members WHERE {where_sql} ORDER BY name LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "data": data
    }

@app.get("/api/members/{mp_code}", tags=["Members"])
def get_member(mp_code: int, db = Depends(get_db)):
    """Get specific member by mp_code"""
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM lok_sabha_members WHERE mp_code = %s", (mp_code,))
    member = cursor.fetchone()
    cursor.close()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@app.get("/api/member-profile/{mp_code}", response_model=MemberProfile, tags=["Members"])
def get_complete_profile(mp_code: int, db = Depends(get_db)):
    """Get complete member profile with all statistics"""
    cursor = db.cursor(dictionary=True)
    
    # Get member info
    cursor.execute("SELECT * FROM lok_sabha_members WHERE mp_code = %s", (mp_code,))
    member = cursor.fetchone()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) as count FROM assurance WHERE mp_code = %s", (mp_code,))
    assurances = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM gallery WHERE mp_code = %s", (mp_code,))
    gallery = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM member_bills WHERE mp_code = %s", (mp_code,))
    bills = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM member_committees WHERE mp_code = %s", (mp_code,))
    committees = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM member_questions WHERE srno = %s", (mp_code,))
    questions = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM member_debates WHERE srno = %s", (mp_code,))
    debates = cursor.fetchone()['count']
    
    cursor.close()
    
    return {
        "member": member,
        "statistics": {
            "assurances": assurances,
            "gallery_videos": gallery,
            "private_bills": bills,
            "committees": committees,
            "questions": questions,
            "debates": debates
        }
    }

# ============================================================
# ASSURANCES
# ============================================================

@app.get("/api/assurances", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_assurances(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get government assurances"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = []
    params = []
    
    if mp_code:
        where_clauses.append("mp_code = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM assurance WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM assurance WHERE {where_sql} ORDER BY loksabha DESC, session DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# GALLERY
# ============================================================

@app.get("/api/gallery", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_gallery(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get gallery videos"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = []
    params = []
    
    if mp_code:
        where_clauses.append("mp_code = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM gallery WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM gallery WHERE {where_sql} ORDER BY eventDate DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# COMMITTEES
# ============================================================

@app.get("/api/committees", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_committees(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get committee memberships"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["mp_code IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("mp_code = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM member_committees WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM member_committees WHERE {where_sql} ORDER BY loksabha DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# BILLS
# ============================================================

@app.get("/api/bills/private", response_model=PaginatedResponse, tags=["Bills"])
def get_private_bills(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get private member bills"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["mp_code IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("mp_code = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM member_bills WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM member_bills WHERE {where_sql} ORDER BY loksabha DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

@app.get("/api/bills/government", response_model=PaginatedResponse, tags=["Bills"])
def get_government_bills(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get government bills"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["srno IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("srno = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM government_bills WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM government_bills WHERE {where_sql} ORDER BY loksabha DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# QUESTIONS
# ============================================================

@app.get("/api/questions", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_questions(
    mp_code: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get parliamentary questions"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["srno IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("srno = %s")
        params.append(mp_code)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM member_questions WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM member_questions WHERE {where_sql} ORDER BY questionDate DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# DEBATES
# ============================================================

@app.get("/api/debates", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_debates(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get parliamentary debates"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["srno IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("srno = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM member_debates WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM member_debates WHERE {where_sql} ORDER BY loksabha DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# SPECIAL MENTIONS
# ============================================================

@app.get("/api/special-mentions", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_special_mentions(
    mp_code: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get special mentions (Zero hour)"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["srno IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("srno = %s")
        params.append(mp_code)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM member_special_mentions WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM member_special_mentions WHERE {where_sql} ORDER BY madeDate DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# TOURS
# ============================================================

@app.get("/api/tours", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_tours(
    mp_code: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get MP tours"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["srno IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("srno = %s")
        params.append(mp_code)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM mp_tour WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM mp_tour WHERE {where_sql} ORDER BY tour_date DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# ============================================================
# PERSONAL DETAILS
# ============================================================

@app.get("/api/personal-details/{mp_code}", tags=["Member Details"])
def get_personal_details(mp_code: int, db = Depends(get_db)):
    """Get member personal details"""
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM member_personal_details WHERE srno = %s", (mp_code,))
    data = cursor.fetchone()
    cursor.close()
    
    if not data:
        raise HTTPException(status_code=404, detail="Personal details not found")
    return data

@app.get("/api/other-details/{mp_code}", tags=["Member Details"])
def get_other_details(mp_code: int, db = Depends(get_db)):
    """Get member other details"""
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM member_other_details WHERE srno = %s", (mp_code,))
    data = cursor.fetchone()
    cursor.close()
    
    if not data:
        raise HTTPException(status_code=404, detail="Other details not found")
    return data

@app.get("/api/dashboard/{mp_code}", tags=["Member Details"])
def get_dashboard(mp_code: int, db = Depends(get_db)):
    """Get member dashboard statistics"""
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM member_dashboard WHERE srno = %s", (mp_code,))
    data = cursor.fetchone()
    cursor.close()
    
    if not data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return data

@app.get("/api/attendance", response_model=PaginatedResponse, tags=["Parliamentary Activities"])
def get_attendance(
    mp_code: Optional[int] = None,
    loksabha: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get attendance records"""
    cursor = db.cursor(dictionary=True)
    
    where_clauses = ["mp_code IS NOT NULL"]
    params = []
    
    if mp_code:
        where_clauses.append("mp_code = %s")
        params.append(mp_code)
    if loksabha:
        where_clauses.append("loksabha = %s")
        params.append(loksabha)
    
    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * size
    
    cursor.execute(f"SELECT COUNT(*) as total FROM member_attendance WHERE {where_sql}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(
        f"SELECT * FROM member_attendance WHERE {where_sql} LIMIT %s OFFSET %s",
        params + [size, offset]
    )
    data = cursor.fetchall()
    cursor.close()
    
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size, "data": data}

# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '127.0.0.1')
    uvicorn.run(app, host=host, port=port)