"""
models.py
=========
Pydantic models for request/response validation
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime

# ============================================================
# RESPONSE MODELS
# ============================================================

class PaginatedResponse(BaseModel):
    """Standard paginated response"""
    total: int
    page: int
    size: int
    pages: int
    data: List[Any]

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    message: Optional[str] = None

# ============================================================
# MEMBER MODELS
# ============================================================

class Member(BaseModel):
    """Lok Sabha Member"""
    mp_code: Optional[int] = None
    name: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    constituency: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    terms: Optional[str] = None
    status: Optional[str] = None
    profile_link: Optional[str] = None

    class Config:
        from_attributes = True

class MemberProfile(BaseModel):
    """Complete member profile with statistics"""
    member: dict
    statistics: dict

# ============================================================
# ASSURANCE MODELS
# ============================================================

class Assurance(BaseModel):
    """Government assurance"""
    id: Optional[int] = None
    mp_code: Optional[int] = None
    member: Optional[str] = None
    assu_no: Optional[str] = None
    loksabha: Optional[int] = None
    session: Optional[int] = None
    ministry: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================================
# GALLERY MODELS
# ============================================================

class Gallery(BaseModel):
    """Video gallery"""
    id: Optional[int] = None
    mp_code: Optional[int] = None
    mp_name: Optional[str] = None
    loksabha: Optional[int] = None
    session: Optional[int] = None
    subject_title: Optional[str] = None
    videoUrl: Optional[str] = None
    eventDate: Optional[date] = None

    class Config:
        from_attributes = True

# ============================================================
# COMMITTEE MODELS
# ============================================================

class Committee(BaseModel):
    """Committee membership"""
    id: Optional[int] = None
    mp_code: Optional[int] = None
    loksabha: Optional[int] = None
    committeeName: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    class Config:
        from_attributes = True

# ============================================================
# BILL MODELS
# ============================================================

class PrivateBill(BaseModel):
    """Private member bill"""
    id: Optional[int] = None
    mp_code: Optional[int] = None
    loksabha: Optional[int] = None
    session: Optional[int] = None
    billName: Optional[str] = None
    debate_date: Optional[str] = None

    class Config:
        from_attributes = True

class GovernmentBill(BaseModel):
    """Government bill"""
    id: Optional[int] = None
    srno: Optional[int] = None
    loksabha: Optional[int] = None
    session: Optional[int] = None
    bill_title: Optional[str] = None
    debate_date: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================================
# QUESTION MODELS
# ============================================================

class Question(BaseModel):
    """Parliamentary question"""
    questionId: Optional[int] = None
    srno: Optional[int] = None
    questionNo: Optional[str] = None
    questionType: Optional[str] = None
    questionDate: Optional[date] = None
    ministry: Optional[str] = None
    subject: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================================
# DEBATE MODELS
# ============================================================

class Debate(BaseModel):
    """Parliamentary debate"""
    debateId: Optional[int] = None
    srno: Optional[int] = None
    loksabha: Optional[int] = None
    session: Optional[int] = None
    title: Optional[str] = None
    debateDate: Optional[date] = None

    class Config:
        from_attributes = True

# ============================================================
# SPECIAL MENTION MODELS
# ============================================================

class SpecialMention(BaseModel):
    """Special mention (Zero hour)"""
    id: Optional[int] = None
    srno: Optional[int] = None
    mentionNo: Optional[int] = None
    madeDate: Optional[date] = None
    subject: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================================
# TOUR MODELS
# ============================================================

class Tour(BaseModel):
    """MP tour"""
    id: Optional[int] = None
    srno: Optional[int] = None
    purpose: Optional[str] = None
    tour_place: Optional[str] = None
    tour_date: Optional[date] = None

    class Config:
        from_attributes = True

# ============================================================
# DETAIL MODELS
# ============================================================

class PersonalDetails(BaseModel):
    """Personal details"""
    srno: Optional[int] = None
    fatherName: Optional[str] = None
    motherName: Optional[str] = None
    dateBirth: Optional[date] = None
    spouseName: Optional[str] = None
    qualification: Optional[str] = None

    class Config:
        from_attributes = True

class OtherDetails(BaseModel):
    """Other details"""
    srno: Optional[int] = None
    freedomFighter: Optional[str] = None
    countriesVisited: Optional[str] = None
    booksPublished: Optional[str] = None
    sportsInterests: Optional[str] = None

    class Config:
        from_attributes = True

class Dashboard(BaseModel):
    """Dashboard statistics"""
    srno: Optional[int] = None
    questionsCount: Optional[int] = None
    billsCount: Optional[int] = None
    committeeCount: Optional[int] = None
    debatesCount: Optional[int] = None

    class Config:
        from_attributes = True