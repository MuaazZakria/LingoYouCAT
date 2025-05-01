from pydantic import BaseModel
class ProjectCreate(BaseModel):
    id: int
    name: str
    id_short: str