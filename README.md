# Timeattack Code Dojo

제한 시간 기반 코딩 훈련 플랫폼의 MVP입니다. Step 1 기준으로 Next.js 프런트엔드와 Flask API가 한 저장소에서 동작하며, Vercel Preview 배포 구조를 따릅니다.

## 로컬 데모 실행

필수 도구: Node.js 20.9 이상, pnpm 11, Python 3.12 이상

```powershell
pnpm install
pnpm setup:python
Copy-Item .env.example .env.local
pnpm dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 열면 됩니다. 화면의 `Frontend ↔ API 연결 완료`가 보이면 Next.js가 Flask의 `GET /api/health`를 정상 호출한 상태입니다.

`pnpm dev`는 다음 두 프로세스를 함께 실행합니다.

- Next.js: `http://localhost:3000`
- Flask API: `http://127.0.0.1:5328/api/health`

종료는 실행 중인 터미널에서 `Ctrl+C`를 누릅니다.

## 검증 명령

```powershell
pnpm lint
pnpm test
pnpm build
```

한 번에 실행하려면 `pnpm check`를 사용합니다.

## 환경변수와 비밀값

`.env.example`만 Git에 커밋합니다. 실제 토큰은 `.env` 또는 `.env.local`에 넣고, `NEXT_PUBLIC_` 접두사는 브라우저에 공개해도 되는 값에만 사용합니다.

Step 0 외부 서비스 점검은 다음 명령으로 다시 실행할 수 있습니다.

```powershell
.venv\Scripts\python.exe poc\step0_probe.py
```

## 문제 조회 API

Step 3 문제 조회 API는 등록된 12개 문제의 공개 목록과 선택한 모드·언어의 문제 데이터를 반환합니다. 모든 문제는 초보·중수·고수 모드와 Python/C++를 지원합니다.

```text
GET /api/problem?mode=intermediate&language=python
```

특정 문제는 `problem_id`로 조회합니다. `difficulty`는 이전 클라이언트 호환용 선택 필터이며, 생략하면 전체 문제가 표시됩니다. 전체 계약과 오류 형식은 [`docs/step3-problem-api.md`](docs/step3-problem-api.md), 문제은행 검증 방법은 [`docs/step2-problem-bank.md`](docs/step2-problem-bank.md)를 참고하세요.

## 학습 화면

학습 화면은 전체 문제·학습 모드·언어 전환, Monaco 코드 편집기, 미제출 답안 경고, 답안 제출과 채점 결과, 로딩·빈 상태·오류·재시도 UI를 제공합니다. 초보 의사코드는 정답 도출이 불가능하거나 핵심 논리가 틀린 경우에만 오답으로 판정합니다. 모든 모드는 첫 오답 뒤 `정답보기`가 활성화되며, 사용자가 버튼을 누른 뒤에만 별도 풀이 페이지가 정답을 요청합니다. 로컬에서도 제출할 수 있으며, Flask API가 코드 답안은 Judge0로, 의사코드 답안은 Hugging Face로 전송해 채점합니다. 의사코드 채점에는 `.env` 또는 `.env.local`의 `HF_TOKEN`이 필요합니다. 자세한 동작과 검증 방법은 [`docs/step4-learning-ui.md`](docs/step4-learning-ui.md)를 참고하세요.

## Vercel Preview

저장소를 Vercel 프로젝트에 연결하면 Next.js 앱과 `api/index.py`의 Flask 앱이 별도 라우팅 설정 없이 함께 빌드됩니다. Preview 환경의 비밀값은 Vercel 프로젝트 설정에서 별도로 등록하고 저장소에는 넣지 않습니다.

`.vercelignore`는 로컬 토큰 파일, 가상환경, 테스트 결과와 개발 도구 파일이 배포 업로드에 포함되지 않도록 차단합니다.
