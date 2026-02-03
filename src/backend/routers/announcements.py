"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format"""
    if announcement:
        announcement["id"] = str(announcement.pop("_id", ""))
    return announcement


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (based on start and expiration dates)"""
    now = datetime.utcnow().isoformat()
    
    query = {
        "expiration_date": {"$gte": now}
    }
    
    announcements = list(announcements_collection.find(query).sort("created_at", -1))
    
    # Filter by start_date if present
    active_announcements = []
    for announcement in announcements:
        start_date = announcement.get("start_date")
        if start_date is None or start_date <= now:
            active_announcements.append(serialize_announcement(announcement))
    
    return active_announcements


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (for authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    return [serialize_announcement(a) for a in announcements]


@router.post("/create")
def create_announcement(
    title: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement (authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if start_date:
            st_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if st_date >= exp_date:
                raise HTTPException(
                    status_code=400,
                    detail="Start date must be before expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    announcement = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": username,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = result.inserted_id
    
    return serialize_announcement(announcement)


@router.put("/update/{announcement_id}")
def update_announcement(
    announcement_id: str,
    title: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an existing announcement (authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if start_date:
            st_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if st_date >= exp_date:
                raise HTTPException(
                    status_code=400,
                    detail="Start date must be before expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    update_data = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date
    }
    
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    return serialize_announcement(announcement)


@router.delete("/delete/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
