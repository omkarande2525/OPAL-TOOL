from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    token = credentials.credentials

    if token != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    return {"user_id": "test_user", "role": "admin"}