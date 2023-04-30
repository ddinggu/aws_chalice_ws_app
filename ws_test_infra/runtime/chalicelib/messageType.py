from typing import Literal, TypedDict


class DefaultMessageType(TypedDict):
    text: str
    nickname: str
    room_id: str
    send_at: str


class MessageActionType(TypedDict):
    action: Literal["PUT_NICKNAME", "SEND_MESSAGE"]
    data: DefaultMessageType
