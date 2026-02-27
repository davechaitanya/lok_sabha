"""
main.py
=======
FastAPI application for Lok Sabha Database
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from typing import Optional
import os
from dotenv import load_dotenv
import requests as req
from io import BytesIO

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

# ============================================================
# IMAGE PROXY ENDPOINTS
# ============================================================

@app.get("/api/image-proxy", tags=["Utilities"])
async def image_proxy(url: str = Query(..., description="Image URL to proxy")):
    """
    Universal image proxy endpoint - Solves CORS issues for external images
    
    Usage: 
        /api/image-proxy?url=https://sansad.in/images/member123.jpg
    
    Frontend usage:
        <img src="https://your-api.com/api/image-proxy?url=ENCODED_IMAGE_URL" />
    """
    try:
        response = req.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        return StreamingResponse(
            BytesIO(response.content),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image not found: {str(e)}")


@app.get("/api/members/{mp_code}/image", tags=["Members"])
def get_member_image(mp_code: int, db = Depends(get_db)):
    """
    Get member's profile image directly - Returns actual image file
    
    Usage:
        /api/members/344/image
    
    Frontend usage:
        <img src="https://your-api.com/api/members/344/image" alt="Member" />
    
    This endpoint:
    - Fetches the member's image_url from database
    - Proxies the image through your API
    - Solves CORS issues
    - Caches for 24 hours
    """
    cursor = db.cursor(dictionary=True)
    
    # Get member's image URL
    try:
        cursor.execute("SELECT image_url FROM lok_sabha_members WHERE mp_code = %s", (mp_code,))
        member = cursor.fetchone()
    except:
        cursor.execute("SELECT image_url FROM lok_sabha_members WHERE profile_link LIKE %s", (f'%/{mp_code}',))
        member = cursor.fetchone()
    
    cursor.close()
    
    if not member or not member.get('image_url'):
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_url = member['image_url']
    
    try:
        response = req.get(image_url, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        return Response(
            content=response.content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch image: {str(e)}")

# ============================================================
# NEW DATA TRACKING ENDPOINTS
# ============================================================

@app.get("/api/new-data/summary", tags=["New Data"])
def get_new_data_summary(db = Depends(get_db)):
    """Get summary of new data across all tables"""
    cursor = db.cursor(dictionary=True)
    
    tables = [
        'assurance', 'gallery', 'member_attendance', 'member_bills',
        'member_committees', 'member_dashboard', 'government_bills',
        'member_debates', 'member_other_details', 'member_personal_details',
        'member_questions', 'member_special_mentions', 'mp_tour'
    ]
    
    summary = []
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE is_new = TRUE")
        count = cursor.fetchone()['count']
        if count > 0:
            summary.append({"table": table, "new_count": count})
    
    cursor.close()
    return {
        "total_new_records": sum(s['new_count'] for s in summary),
        "tables": summary
    }


@app.get("/api/questions/new", tags=["New Data"])
def get_new_questions(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get only NEW questions that haven't been viewed"""
    cursor = db.cursor(dictionary=True)
    offset = (page - 1) * size
    
    cursor.execute("SELECT COUNT(*) as total FROM member_questions WHERE is_new = TRUE")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT * FROM member_questions 
        WHERE is_new = TRUE 
        ORDER BY scraped_at DESC 
        LIMIT %s OFFSET %s
    """, (size, offset))
    data = cursor.fetchall()
    cursor.close()
    
    return {
        "total_new": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "data": data
    }


@app.get("/api/debates/new", tags=["New Data"])
def get_new_debates(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get only NEW debates"""
    cursor = db.cursor(dictionary=True)
    offset = (page - 1) * size
    
    cursor.execute("SELECT COUNT(*) as total FROM member_debates WHERE is_new = TRUE")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT * FROM member_debates 
        WHERE is_new = TRUE 
        ORDER BY scraped_at DESC 
        LIMIT %s OFFSET %s
    """, (size, offset))
    data = cursor.fetchall()
    cursor.close()
    
    return {"total_new": total, "page": page, "size": size, "data": data}


@app.get("/api/bills/government/new", tags=["New Data"])
def get_new_government_bills(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get only NEW government bills"""
    cursor = db.cursor(dictionary=True)
    offset = (page - 1) * size
    
    cursor.execute("SELECT COUNT(*) as total FROM government_bills WHERE is_new = TRUE")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT * FROM government_bills 
        WHERE is_new = TRUE 
        ORDER BY scraped_at DESC 
        LIMIT %s OFFSET %s
    """, (size, offset))
    data = cursor.fetchall()
    cursor.close()
    
    return {"total_new": total, "page": page, "size": size, "data": data}


@app.get("/api/special-mentions/new", tags=["New Data"])
def get_new_special_mentions(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
):
    """Get only NEW special mentions"""
    cursor = db.cursor(dictionary=True)
    offset = (page - 1) * size
    
    cursor.execute("SELECT COUNT(*) as total FROM member_special_mentions WHERE is_new = TRUE")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT * FROM member_special_mentions 
        WHERE is_new = TRUE 
        ORDER BY scraped_at DESC 
        LIMIT %s OFFSET %s
    """, (size, offset))
    data = cursor.fetchall()
    cursor.close()
    
    return {"total_new": total, "page": page, "size": size, "data": data}


@app.get("/api/members/{mp_code}/new-activities", tags=["New Data"])
def get_member_new_activities(mp_code: int, db = Depends(get_db)):
    """Get ALL new activities for a specific member"""
    cursor = db.cursor(dictionary=True)
    
    activities = {}
    
    # New questions
    cursor.execute("""
        SELECT COUNT(*) as count FROM member_questions 
        WHERE mp_code = %s AND is_new = TRUE
    """, (mp_code,))
    activities['new_questions'] = cursor.fetchone()['count']
    
    # New debates
    cursor.execute("""
        SELECT COUNT(*) as count FROM member_debates 
        WHERE mp_code = %s AND is_new = TRUE
    """, (mp_code,))
    activities['new_debates'] = cursor.fetchone()['count']
    
    # New bills
    cursor.execute("""
        SELECT COUNT(*) as count FROM member_bills 
        WHERE mp_code = %s AND is_new = TRUE
    """, (mp_code,))
    activities['new_bills'] = cursor.fetchone()['count']
    
    # New special mentions
    cursor.execute("""
        SELECT COUNT(*) as count FROM member_special_mentions 
        WHERE mp_code = %s AND is_new = TRUE
    """, (mp_code,))
    activities['new_mentions'] = cursor.fetchone()['count']
    
    cursor.close()
    
    return {
        "mp_code": mp_code,
        "activities": activities,
        "total_new": sum(activities.values())
    }


@app.post("/api/questions/{question_id}/mark-read", tags=["New Data"])
def mark_question_read(question_id: int, db = Depends(get_db)):
    """Mark a question as read (not new anymore)"""
    cursor = db.cursor()
    cursor.execute("""
        UPDATE member_questions 
        SET is_new = FALSE 
        WHERE questionId = %s
    """, (question_id,))
    db.commit()
    affected = cursor.rowcount
    cursor.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {"status": "success", "message": "Question marked as read"}


@app.post("/api/debates/{debate_id}/mark-read", tags=["New Data"])
def mark_debate_read(debate_id: int, db = Depends(get_db)):
    """Mark a debate as read"""
    cursor = db.cursor()
    cursor.execute("""
        UPDATE member_debates 
        SET is_new = FALSE 
        WHERE debateId = %s
    """, (debate_id,))
    db.commit()
    affected = cursor.rowcount
    cursor.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    return {"status": "success", "message": "Debate marked as read"}


@app.post("/api/new-data/mark-all-read/{table_name}", tags=["New Data"])
def mark_all_read(table_name: str, db = Depends(get_db)):
    """Mark all records in a table as read (is_new = FALSE)"""
    allowed_tables = [
        'member_questions', 'member_debates', 'member_special_mentions',
        'government_bills', 'member_bills', 'assurance', 'gallery'
    ]
    
    if table_name not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    cursor = db.cursor()
    cursor.execute(f"UPDATE {table_name} SET is_new = FALSE WHERE is_new = TRUE")
    db.commit()
    affected = cursor.rowcount
    cursor.close()
    
    return {
        "status": "success",
        "table": table_name,
        "records_marked": affected
    }


@app.get("/api/scrape-tracker", tags=["New Data"])
def get_scrape_tracker(db = Depends(get_db)):
    """Get scraping statistics for all tables"""
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            table_name,
            last_max_id,
            last_scrape_time,
            new_records_count,
            total_records,
            scrape_status
        FROM scrape_tracker
        ORDER BY last_scrape_time DESC
    """)
    data = cursor.fetchall()
    cursor.close()
    
    return {"trackers": data}

# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '127.0.0.1')
    uvicorn.run(app, host=host, port=port)