from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if token != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return {"user_id": "test_user", "role": "admin"}
