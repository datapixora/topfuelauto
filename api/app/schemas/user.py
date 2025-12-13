from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    is_pro: bool = False


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int