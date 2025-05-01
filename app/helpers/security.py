from fastapi import Depends, HTTPException, status

from app.crud.user import get_current_user
from app.models.user import User, Role


def require_role(required_role: Role):
    def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource"
            )
        return current_user
    return role_dependency
