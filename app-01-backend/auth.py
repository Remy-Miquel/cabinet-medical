"""
APP-01 — Authentification (JWT) et RBAC — version durcie
Sécurité applicative : JWT avec jti (anti-rejeu), expiration, validation stricte.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# --- Signature des tokens ---
# Le secret DOIT être fort et fourni par l'environnement. En son absence,
# on refuse de démarrer avec un secret par défaut (sécurité).
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET manquant ou trop court (>= 32 caractères requis). "
        "Générez-le avec : openssl rand -hex 32"
    )

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 15          # expiration courte (limite la fenêtre de rejeu)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Liste de révocation en mémoire (jti des tokens invalidés à la déconnexion).
# En production : Redis. Ici, suffisant pour la démo.
_revoked_jti: set[str] = set()


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(email: str, role: str, uid: int) -> str:
    """
    Génère un JWT signé contenant :
    - sub (email), role, uid
    - exp (expiration), iat (émission), jti (identifiant unique anti-rejeu)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "uid": uid,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),          # identifiant unique du token
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def revoke_token(jti: str):
    """Invalide un token (appelé à la déconnexion)."""
    _revoked_jti.add(jti)


def decode_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Décode et valide strictement le JWT :
    - signature (rejette tout token forgé)
    - expiration
    - présence du jti et non-révocation (anti-rejeu)
    """
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide, expiré ou révoqué",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti"]},   # champs obligatoires
        )
    except JWTError:
        raise cred_exc

    jti = payload.get("jti")
    if not jti or jti in _revoked_jti:      # token révoqué ou sans identifiant
        raise cred_exc
    if payload.get("sub") is None:
        raise cred_exc
    return payload


def require_role(*roles_autorises: str):
    """Dépendance RBAC : n'autorise que les rôles listés."""
    def checker(payload: dict = Depends(decode_token)) -> dict:
        if payload.get("role") not in roles_autorises:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé : rôle '{payload.get('role')}' non autorisé",
            )
        return payload
    return checker
