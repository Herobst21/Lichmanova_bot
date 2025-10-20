import uuid
def corr_id() -> str:
    return uuid.uuid4().hex
