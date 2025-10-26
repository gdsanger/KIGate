"""
Admin authentication module for securing the /admin area
"""
import secrets
from typing import Annotated
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import bcrypt

# HTTP Basic Security
security = HTTPBasic()

# Static admin credentials (hashed)
ADMIN_USERNAME = "admin"
# Password: Opg#842+9914
ADMIN_PASSWORD_HASH = "$2b$12$D6cpHoeUMmsmfTg/xg2Pae5XlWNBL5w2i/Q/fAZLEMACnCsdXqJlO"

templates = Jinja2Templates(directory="templates")


def verify_admin_password(password: str) -> bool:
    """Verify admin password against stored hash"""
    return bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))


def get_admin_credentials(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
) -> HTTPBasicCredentials:
    """
    Verify admin credentials using HTTP Basic Authentication
    """
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), ADMIN_USERNAME.encode("utf8")
    )
    is_correct_password = verify_admin_password(credentials.password)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Admin-Anmeldedaten",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials


def get_admin_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(get_admin_credentials)]
) -> str:
    """
    Get authenticated admin user
    """
    return credentials.username


async def admin_login_page(request: Request) -> HTMLResponse:
    """
    Show admin login page for browser access
    """
    return templates.TemplateResponse("admin_login.html", {
        "request": request
    })