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

Step 3 문제 조회 API는 난이도, 모드, 언어에 맞는 공개 데이터만 반환합니다.

```text
GET /api/problem?difficulty=easy&mode=intermediate&language=python
```

특정 문제는 `problem_id` 선택 파라미터로 조회할 수 있습니다. 전체 계약과 오류 형식은 [`docs/step3-problem-api.md`](docs/step3-problem-api.md), 문제은행 검증 방법은 [`docs/step2-problem-bank.md`](docs/step2-problem-bank.md)를 참고하세요.

## Vercel Preview

저장소를 Vercel 프로젝트에 연결하면 Next.js 앱과 `api/index.py`의 Flask 앱이 별도 라우팅 설정 없이 함께 빌드됩니다. Preview 환경의 비밀값은 Vercel 프로젝트 설정에서 별도로 등록하고 저장소에는 넣지 않습니다.

`.vercelignore`는 로컬 토큰 파일, 가상환경, 테스트 결과와 개발 도구 파일이 배포 업로드에 포함되지 않도록 차단합니다.
