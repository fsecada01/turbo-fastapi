import uuid

from pydantic import BaseModel

# class Todo:
#     def __init__(self, task):
#         self.id = uuid.uuid4().hex
#         self.task = task
#         self.completed = False


class Todo(BaseModel):
    id: uuid.UUID = uuid.uuid4().hex
    task: str
    completed: bool = False
