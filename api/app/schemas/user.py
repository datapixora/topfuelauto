from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    is_admin: bool = False
    is_active: bool = True
    plan_id: int | None = None
    plan_name: str | None = None
    plan_key: str | None = None
    is_pro: bool | None = None  # deprecated


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
