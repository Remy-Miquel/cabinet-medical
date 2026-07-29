"""
APP-01 — Authentification (JWT) et contrôle d'accès basé sur les rôles (RBAC)
Cabinet médical — dossier technique section 5.3.3

Le token JWT porte l'identité ET le rôle. Chaque endpoint protégé vérifie
le rôle avant de répondre : c'est le cœur du RBAC applicatif.
"""
import os
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# --- Hachage des mots de passe ---
# bcrypt : jamais de mot de passe stocké ou comparé en clair.
# bcrypt limite le secret à 72 octets : on tronque proprement au besoin.

# --- Signature des tokens ---
# La clé secrète vient de l'environnement (jamais en dur en prod).
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-a-changer-en-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]      # bcrypt : max 72 octets
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(username: str, role: str, user_id: int) -> str:
    """Génère un JWT contenant l'identité et le rôle."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "uid": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Décode et valide le JWT. Rejette tout token invalide ou expiré."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise cred_exc
        return payload
    except JWTError:
        raise cred_exc


def require_role(*roles_autorises: str):
    """
    Fabrique une dépendance qui n'autorise que certains rôles.
    Usage : Depends(require_role("medecin"))  ou  require_role("medecin","secretariat")
    C'est le point de contrôle RBAC réutilisable sur chaque endpoint.
    """
    def checker(payload: dict = Depends(decode_token)) -> dict:
        if payload.get("role") not in roles_autorises:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé : rôle '{payload.get('role')}' non autorisé pour cette ressource",
            )
        return payload
    return checker
