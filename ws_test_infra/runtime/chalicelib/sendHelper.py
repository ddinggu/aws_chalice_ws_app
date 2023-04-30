import json

from chalice.app import WebsocketDisconnectedError, Chalice

from .storages import ConnectionStorage
from .messageType import DefaultMessageType


class Sender(object):
    """
    API GW에서 제공하는 connection_id 기반 웹 소켓 메세지를 발송하는 클래스
    """

    def __init__(self, storage: ConnectionStorage, app: Chalice) -> None:
        """Sender 객체 초기화

        :param storage (ConnectionStorage): Connection 테이블
        :param app (Chliace): boto 세션이 유지되고 있는 Chalice app
        """
        self._storage = storage
        self._app = app

    def send_message(self, connection_id: str, message: str) -> None:
        """API GW를 통해 웹 소켓 연결되어 있는 유저들에게 메세지 전송

        :param connection_id (str): API GW에서 받아온 connection_id
        :param message (str): 메세지
        """
        try:
            self._app.websocket_api.send(connection_id, message)
            print(f"{connection_id}에게 {message} 발송")

        except WebsocketDisconnectedError as e:
            self._storage.delete_connection(e.connection_id)
        except Exception as error:
            raise error

    def brodcast(self, message: DefaultMessageType, sender_id: str) -> None:
        """모든 웹 소켓 연결 유저에게 메세지 전파
           현재 테스트에선 한 방에 모두 접속해있다고 가정했기 때문에 connection_id를 해당 함수에서 가져옴

        :param message (DefaultMessageType): 발송 메세지 { nickname, text, room_id, send_at }
        """
        try:
            connection_ids = self._storage.get_all_connection_ids(message["room_id"])

            for c_id in connection_ids:
                if c_id == sender_id:
                    continue

                self.send_message(c_id, json.dumps(message))

        except Exception as error:
            raise error
