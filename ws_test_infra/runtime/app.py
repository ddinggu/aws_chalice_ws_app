import json
import gzip
import os

from boto3.session import Session
from botocore import session as botocore_session

from chalice.app import ConvertToMiddleware, WebsocketEvent, Chalice, Response

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from chalicelib.storages import MessageStorage, ConnectionStorage
from chalicelib.sendHelper import Sender

# 람다 프로비저닝 컨테이너에서 사용할 botocore Connetion 세션 유지
session = botocore_session.Session()
session.set_config_variable("retries", {"max_attempts": 10})

# SAM 도구인 Chalice 프로젝트 생성 및 API GW에서 웹 소켓 사용을 위한 설정
app = Chalice(app_name="wschat-function")
app.websocket_api.session = Session(botocore_session=session)
app.experimental_feature_flags.update(["WEBSOCKETS"])

app.api.binary_types.append("application/json")

# Lambda Powertools를 활용한 CloudWatch 메트릭 트레이싱 관련 설정
tracer = Tracer(service=app.app_name)
logger = Logger(service=app.app_name)
http_metrics = Metrics(namespace=app.app_name, service="http")
websocket_metrics = Metrics(namespace=app.app_name, service="websocket")

app.register_middleware(ConvertToMiddleware(tracer.capture_lambda_handler(capture_response=False)))
app.register_middleware(ConvertToMiddleware(logger.inject_lambda_context(log_event=True)))
app.register_middleware(
    ConvertToMiddleware(http_metrics.log_metrics(capture_cold_start_metric=True)), "http"
)
app.register_middleware(
    ConvertToMiddleware(websocket_metrics.log_metrics(capture_cold_start_metric=True)), "websocket"
)

# AWS CDK를 통해 프로비저닝된 리소스의 정보를 Import
conn_table_name = os.environ.get("CONNECTIONS_TABLE_NAME", "")
msg_table_name = os.environ.get("MESSAGES_TABLE_NAME", "")

# 웹 소켓 서비스 로직 Import
MSG_STORAGE = MessageStorage(msg_table_name)
CON_STORAGE = ConnectionStorage(conn_table_name)
SENDER = Sender(CON_STORAGE, app)


@app.route("/room/{room_id}", methods=["GET"])
def room_messages(room_id):
    r = MSG_STORAGE.get_all_room_messages(room_id)

    blob = json.dumps(r).encode("utf-8")
    payload = gzip.compress(blob)
    custom_headers = {"Content-Type": "application/json", "Content-Encoding": "gzip"}

    return Response(body=payload, status_code=200, headers=custom_headers)


@app.on_ws_connect(name="ws_connection")
def ws_connect(event: WebsocketEvent):
    websocket_metrics.add_metric(name="SuccessfulConnection", unit=MetricUnit.Count, value=1)
    websocket_metrics.add_metadata(key="connection_id", value=event.connection_id)
    CON_STORAGE.create_connection(event.connection_id)

    logger.debug("웹 소켓 연결", extra={"connection_id": event.connection_id})


@app.on_ws_disconnect(name="ws_disconnection")
def ws_disconnect(event: WebsocketEvent):
    websocket_metrics.add_metric(name="Disconnection", unit=MetricUnit.Count, value=1)
    CON_STORAGE.delete_connection(event.connection_id)

    logger.debug("웹 소켓 연결해제", extra={"connection_id": event.connection_id})


@app.on_ws_message(name="ws_message")
def ws_message(event: WebsocketEvent):
    connection_id = event.connection_id
    action_type = event.json_body["action"]
    message = event.json_body["data"]

    if action_type == "PUT_NICKNAME":
        websocket_metrics.add_metric(name="Subscription", unit=MetricUnit.Count, value=1)
        CON_STORAGE.set_connection_info(connection_id, message["nickname"], message["room_id"])

        logger.debug(f"{connection_id}의 구독", extra=message)

    elif action_type == "SEND_MESSAGE":
        websocket_metrics.add_metric(name="SendMessage", unit=MetricUnit.Count, value=1)
        SENDER.brodcast(message, connection_id)
        MSG_STORAGE.put_message(message)

        logger.debug(f"{connection_id}의 {action_type} 메세지", extra=message)

    else:
        logger.error(f"허용하지 않는 타입: {action_type}", extra=message)
        websocket_metrics.add_metric(name="UnAuthorizedActionType", unit=MetricUnit.Count, value=1)

        return {"statusCode": 200, "error_msg": "허용하지 않는 타입"}
