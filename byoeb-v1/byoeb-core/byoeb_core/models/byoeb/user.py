from typing import List, Optional
from pydantic import BaseModel, Field

class UserInfo(BaseModel):
    user_id: str
    user_language: str
    phone_number_id: str,
    user_type: str
    test_user: bool