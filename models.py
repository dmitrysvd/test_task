from uuid import UUID
from pydantic import BaseModel


class UploadedFileModel(BaseModel):
    uid: str
    size: int
    format: str
    original_name: str
    extension: str
    is_uploaded_to_cloud: bool