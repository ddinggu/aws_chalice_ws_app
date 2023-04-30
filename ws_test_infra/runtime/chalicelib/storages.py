import boto3

from uuid import uuid4  ## UUID 객체반환하므로 str로 변경필요
from typing import List
from boto3.dynamodb.conditions import Key as TableKey

from .messageType import DefaultMessageType


class ConnectionStorage(object):
    """Connection Table과의 연동하는 클래스"""

    def __init__(self, table_name: str):
        """DynamoDB 테이블 초기화

        :param table_name (str): CDK에서 전달받아 실행될 DynamoDB 테이블 명
        """
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        self._table = table

    def create_connection(self, connection_id: str) -> None:
        """웹 소켓 연결 생성 시 테이블에 적제

        :param connection_id (str): API GW에서 받아온 connection_id
        """
        try:
            self._table.put_item(Item={"PK": connection_id, "SK": "Nickname#"})
        except Exception as error:
            raise error

    def set_connection_info(self, connection_id: str, nickname: str, room_id: str) -> None:
        """유저 채팅방 입장 시, 입장관련 정보 등록

        :params  connection_id (str): API GW에서 받아온 connection_id
        :params  nickname (str): 입장하는 유저 닉네임
        :params  room_id (str): 입장하는 채팅방 id
        """
        try:
            self._table.delete_item(Key={"PK": connection_id, "SK": "Nickname#"})
            self._table.put_item(Item={"PK": connection_id, "SK": "Nickname#%s" % nickname})
            self._table.put_item(Item={"PK": connection_id, "SK": "Room#%s" % room_id})
        except Exception as error:
            raise error

    def delete_connection(self, connection_id: str) -> None:
        """웹 소켓 연결이 끊기면, 테이블에서 연결관련 정보 제거

        :param connection_id (str): API GW에서 받아온 connection_id
        """
        try:
            r = self._table.query(
                KeyConditionExpression=(TableKey("PK").eq(connection_id)),
                Select="ALL_ATTRIBUTES",
            )

            for item in r["Items"]:
                self._table.delete_item(Key={"PK": connection_id, "SK": item["SK"]})

        except Exception as error:
            raise error

    def get_all_connection_ids(self, room_id: str) -> List[str]:
        """메세지 브로드 캐스팅을 위해 DB에 적재된 모든 connection_id를 출력

        :params room_id: 현재 접속한 채팅방
        :return List[str]: 현재 연결되어 있는 connection_id의 집합
        """
        try:
            r = self._table.query(
                IndexName="ReverseLookup",
                KeyConditionExpression=(TableKey("SK").eq("Room#%s" % room_id)),
                Select="ALL_ATTRIBUTES",
            )

            return [item["PK"] for item in r["Items"]]
        except Exception as error:
            raise error


class MessageStorage(object):
    """Messages 테이블과 연동되는 클래스"""

    def __init__(self, table_name: str) -> None:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        self._table = table

    def get_all_room_messages(self, room_id: str):
        return self._table.query(
            KeyConditionExpression=(TableKey("PK").eq("Room#%s" % room_id)),
            Select="ALL_ATTRIBUTES",
        )["Items"]

    def put_message(self, body: DefaultMessageType) -> None:
        try:
            self._table.put_item(
                Item={
                    "PK": "Room#%s" % body["room_id"],
                    "SK": body["send_at"],
                    "message": {
                        "id": str(uuid4()),
                        "text": body["text"],
                        "nickname": body["nickname"],
                    },
                }
            )
        except Exception as error:
            print("put_message에러")
            raise error
