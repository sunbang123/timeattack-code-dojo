# Step 2 문제 은행 설계

## 목표

세 모드와 Python/C++를 하나의 버전 규칙으로 표현하면서 정답과 비공개 테스트가 클라이언트 응답에 포함되지 않도록 분리한다.

## 디렉터리 경계

- `problem_bank/public/`: 문제 설명, 공개 예시, 중수 스켈레톤, 고수 최소 템플릿. API가 클라이언트에 반환할 수 있는 데이터다.
- `problem_bank/private/`: 초보 평가 루브릭, Python/C++ 기준 정답, 비공개 테스트. 서버에서만 읽는다.
- `problem_bank/schemas/`: 공개/비공개 JSON 문서의 계약이다.
- `problem_bank/manifest.json`: 문제 ID, 난이도, 버전을 한곳에서 관리한다.

기본 문제은행에는 이전 기본 문제 6개와 확장 문제 6개를 합친 12개가 있으며, AI로 생성한 문제를 추가할 수 있다. 각 문제는 초보·중수·고수 세 모드와 Python/C++를 모두 지원한다.

브라우저 코드에서는 `problem_bank/private`를 import하지 않는다. Step 3의 문제 조회 API는 공개 문서만 직렬화하며, 채점 API와 오답 권한을 검증한 풀이 API만 서버에서 비공개 문서를 읽는다. 저장소가 공개되는 경우 비공개 문서는 운영 전 암호화된 저장소나 접근 제한 저장소로 옮겨야 한다.

## 버전 규칙

- `schema_version`: 문서 구조가 바뀔 때 올린다. 현재 `1.0.0`이다.
- `version`: 문제 내용, 정답 또는 테스트가 바뀔 때 정수로 올린다.
- 공개/비공개 문서의 `id`/`problem_id`와 `version`은 반드시 일치해야 한다.
- 이미 제출 결과가 존재하는 문제는 기존 버전을 덮어쓰지 않고 새 버전을 추가한다.

## 모드 매핑

- `beginner`: 자연어 의사코드 입력과 서버 전용 루브릭 평가
- `intermediate`: 언어별 TODO 스켈레톤 제공
- `expert`: 입출력 처리만 있는 최소 템플릿 제공

## 검증

```powershell
pnpm test:problems
pnpm test:problems:cpp
```

첫 명령은 등록된 모든 문제의 스키마 필수 필드, 난이도 분포, 세 모드 지원, 공개/비공개 경계, 루브릭 가중치와 Python 기준 정답을 확인한다. 두 번째 명령은 로컬 C++17 컴파일러로 C++ 기준 정답까지 검증하고 `artifacts/step2-validation-results.json`에 증빙을 남긴다.

`pnpm test:problems:judge0`는 같은 C++ 코드와 테스트 데이터를 외부 Judge0로 전송하므로, 해당 데이터의 외부 반출이 허용된 환경에서만 사용한다.
