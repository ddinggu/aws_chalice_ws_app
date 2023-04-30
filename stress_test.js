import { randomString, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.1.0/index.js';
import { WebSocket } from 'k6/experimental/websockets';
import { setTimeout, clearTimeout, setInterval, clearInterval } from 'k6/experimental/timers';

const WSS_URL = '<웹 소켓 테스트용 URL>';
const ROOD_ID = '<테스트용 채팅 Room ID>';
const sessionDuration = randomIntBetween(80000, 100000);

const set_default_message = (type, msg) => ({
  action: type,
  data: {
    nickname: msg.nickname,
    room_id: ROOD_ID,
  },
});

function get_message(message_type = 'NONE', args) {
  const message = set_default_message(message_type, args);

  if (message_type === 'PUT_NICKNAME') {
    return message;
  }

  if (message_type === 'SEND_MESSAGE') {
    message.data.text = args.text;
    message.data.send_at = new Date().toISOString();

    return message;
  }

  return { action: message_type };
}

export const options = {
  vus: 10,
  iterations: 10,
};

export default function () {
  for (let i = 0; i < 4; i++) {
    startWebSocketWorker(i);
  }
}

function startWebSocketWorker(id) {
  const ws = new WebSocket(`${WSS_URL}`);

  ws.addEventListener('error', () => {
    console.log('연결 오류!');
  });

  ws.addEventListener('open', () => {
    const randomNickname = randomString(7);

    ws.send(JSON.stringify(get_message('PUT_NICKNAME', { nickname: randomNickname })));

    ws.addEventListener('message', (e) => {
      const msg = JSON.parse(e.data);

      console.log(`VU ${__VU}:${id} 메세지 수신: ${msg.nickname}님이 ${msg.text}라고 전달`);
    });

    // 2-3초 마다 랜덤매세지 발송
    const intervalId = setInterval(() => {
      const randomMessageLength = randomIntBetween(10, 30);

      ws.send(
        JSON.stringify(
          get_message('SEND_MESSAGE', {
            nickname: randomNickname,
            text: randomString(randomMessageLength),
          })
        )
      );
    }, randomIntBetween(3000, 4000));

    // after a sessionDuration stop sending messages and leave the room
    const leaveChatRoom = setTimeout(() => {
      clearInterval(intervalId);
      console.log(`VU ${__VU}:${id}: 랜덤 세션시간인 ${sessionDuration}ms가 지나서, 채팅 종료`);
    }, sessionDuration);

    // after a sessionDuration + 3s close the connection
    const disconnectWebSocket = setTimeout(() => {
      console.log(`채팅 종료 3초 후 Gracefully Disconnection`);
      ws.close();
    }, sessionDuration + 3000);

    // when connection is closing, clean up the previously created timers
    ws.addEventListener('close', () => {
      clearTimeout(leaveChatRoom);
      clearTimeout(disconnectWebSocket);
    });
  });
}
