# AWS Chalice with CDK

---

`pip install "chalice[cdkv2]"` 추가 설치 필요

---

## 디렉토리 구조

```
.
├── README.md
├── .python-version # Lambda 파이썬 최신 지원 버전
├── infrastructure # AWS CDK 코드
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   └── stacks
│       ├── __init__.py
│       └── chaliceapp.py
├── requirements.txt  # Chalice SAM 프로젝트 코드
├── stress_test.js # 서비스 로직 스트레스 테스트 코드
└── runtime
    ├── app.py
    └── requirements.txt
```

### 배포 방법

Chalice 커맨드로 CDK 통합이 불가능하므로 aws-cdk 패키지 추가 설치 필요 `npm i -g aws-cdk`

1. 프로젝트 루트 폴더에서 requirements.txt의 패키지 설치
2. `/infrastructure` 디렉토리 이동
3. `cdk bootstrap` 으로 리소스 배포를 위한 환경 프로비저닝
4. 배포는 `cdk deploy`

_👀!! CDK로 통합하여 작업할 시 모든 명령어는 aws-cdk에 종속되며, `/infrastructure` 디렉토리에서 실행해야함._

### Chalice CDK

CDK 스택은 Chalice CDK 스택을 이용하는데, 환경변수 및 URL, Role 등 리소스들을 매핑하여 Chalice에게 간편하게 전달할 수 있는 이점이 있다.
아래의 예시를 통해 CDK 사용 및 환경변수 전달방법을 확인해보자

```python
from chalice.cdk import Chalice

RUNTIME_SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), os.pardir, 'runtime')

class ChaliceApp(cdk.Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.dynamodb_table = self._create_ddb_table()
        self.chalice = Chalice(
            self, 'ChaliceApp', source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                'environment_variables': {
                    'APP_TABLE_NAME': self.dynamodb_table.table_name
                }
            }
        )
        self.dynamodb_table.grant_read_write_data(
            self.chalice.get_role('DefaultRole')
        )

        def _create_ddb_table(self):
            # DynamoDB 생성 로직
```

클래스 초기화 함수에서 DynamoDB를 생성한 후 연결에 필요한 테이블 명을 `self.chalice()` 메소드를 통해 환경변수로 전달하는데,
이 환경변수는 `./runtime/.chalice/config.json` 에 있는 Chalice config 정보에 병합해서 사용할 수 있는 로직의 예시이다.
