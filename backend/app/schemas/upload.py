from pydantic import BaseModel


class ImageUploadOut(BaseModel):
    url: str
