from pydantic import BaseModel


class Condition(BaseModel):
    value: str
    var: str
    type: str
    name: str

