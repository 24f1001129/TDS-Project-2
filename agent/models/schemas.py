from pydantic import BaseModel

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str