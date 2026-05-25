from uuid import UUID, uuid4


def generate_investigation_id() -> UUID:
    return uuid4()
