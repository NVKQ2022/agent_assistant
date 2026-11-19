from typing import Dict, List, Optional
import uuid
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from backend.models import UserProfile, RequestCreate, ServiceRequest

app = FastAPI(
    title="Service Request Backend API",
    version="0.1.0",
    description="Backend service to handle form submissions and user profiles"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock Employee Directory (Identity Provider)
USERS_DB: Dict[str, UserProfile] = {
    "alice": UserProfile(
        user_id="alice",
        name="Alice Wonderland",
        email="alice@company.com",
        department="Engineering",
        role="Senior Developer"
    ),
    "bob": UserProfile(
        user_id="bob",
        name="Bob Builder",
        email="bob@company.com",
        department="Sales & Accounts",
        role="Account Executive"
    ),
    "charlie": UserProfile(
        user_id="charlie",
        name="Charlie Chaplin",
        email="charlie@company.com",
        department="People Operations",
        role="HR Coordinator"
    ),
}

# In-memory storage for submitted form requests
REQUESTS_DB: List[ServiceRequest] = [
    ServiceRequest(
        id="REQ-101",
        user_id="alice",
        user_name="Alice Wonderland",
        user_email="alice@company.com",
        department="Engineering",
        category="Hardware",
        priority="Medium",
        description="Dual 27-inch 4K Monitors for development workstation",
        status="Approved",
        submitted_via="web_form",
    ),
    ServiceRequest(
        id="REQ-102",
        user_id="bob",
        user_name="Bob Builder",
        user_email="bob@company.com",
        department="Sales & Accounts",
        category="Software",
        priority="High",
        description="Salesforce CRM Enterprise Seat license upgrade",
        status="Pending Approval",
        submitted_via="web_form",
    ),
]


def resolve_user(x_user_id: Optional[str] = Header(None)) -> UserProfile:
    """Extract authenticated user profile from incoming HTTP header."""
    uid = (x_user_id or "alice").lower()
    if uid not in USERS_DB:
        # Create an ad-hoc profile if user isn't in mock DB
        return UserProfile(
            user_id=uid,
            name=uid.capitalize(),
            email=f"{uid}@company.com",
            department="General",
            role="Staff Member"
        )
    return USERS_DB[uid]


@app.get("/health", tags=["System"])
def health():
    return {"service": "backend", "status": "healthy", "port": 8002}


@app.get("/api/me", response_model=UserProfile, tags=["User"])
def get_current_user_profile(user: UserProfile = Header(None)):
    # Fallback if dependency wasn't directly invoked
    return user


@app.get("/api/users/{user_id}", response_model=UserProfile, tags=["User"])
def get_user_profile_by_id(user_id: str):
    uid = user_id.lower()
    if uid in USERS_DB:
        return USERS_DB[uid]
    return UserProfile(
        user_id=uid,
        name=uid.capitalize(),
        email=f"{uid}@company.com",
        department="General",
        role="Staff Member"
    )


@app.post("/api/requests", response_model=ServiceRequest, status_code=status.HTTP_201_CREATED, tags=["Requests"])
def submit_service_request(
    payload: RequestCreate,
    x_user_id: Optional[str] = Header("alice"),
    x_submitted_via: Optional[str] = Header("web_form")
):
    """
    Submits a new service request form.
    Identity is verified via the X-User-Id HTTP header.
    """
    user = resolve_user(x_user_id)
    req_id = f"REQ-{len(REQUESTS_DB) + 101}"

    new_request = ServiceRequest(
        id=req_id,
        user_id=user.user_id,
        user_name=user.name,
        user_email=user.email,
        department=user.department,
        category=payload.category,
        priority=payload.priority,
        description=payload.description,
        status="Pending Approval",
        submitted_via=x_submitted_via or "web_form",
    )
    REQUESTS_DB.append(new_request)
    return new_request


@app.get("/api/requests", response_model=List[ServiceRequest], tags=["Requests"])
def list_user_requests(x_user_id: Optional[str] = Header("alice")):
    """
    Returns service requests belonging strictly to the authenticated user.
    """
    user = resolve_user(x_user_id)
    # Strictly filter by calling user's identity
    return [r for r in REQUESTS_DB if r.user_id.lower() == user.user_id.lower()]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
