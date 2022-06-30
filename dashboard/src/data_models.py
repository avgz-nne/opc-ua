from pydantic import BaseModel


class ConnectedPorts(BaseModel):
    numbers: list[int]
    names: list[str]


class Reading(BaseModel):
    values: list[float]
