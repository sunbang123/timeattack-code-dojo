# Step 4 학습 화면

Step 4는 문제은행 API를 공통 학습 화면에 연결하고, 난이도·문제·학습 모드·언어를 한 화면에서 전환할 수 있도록 구현합니다.

## 편집기 정책

- 초보(`beginner`): 의사코드를 작성하는 일반 텍스트 영역
- 중수(`intermediate`): 제공된 TODO 뼈대 코드를 수정하는 Monaco Editor
- 고수(`expert`): 최소 템플릿에서 시작하는 Monaco Editor
- 767px 이하: Monaco가 공식적으로 모바일 브라우저를 지원하지 않으므로 같은 값을 사용하는 경량 코드 텍스트 영역으로 대체

Monaco 런타임 파일은 `postinstall`, `dev:web`, `build` 전에 `scripts/copy-monaco-assets.mjs`가 `public/monaco/vs`로 복사합니다. 브라우저에서는 외부 CDN 대신 `/monaco/vs`를 사용합니다.

## 상태와 안전장치

- 문제 API 요청 중에는 스켈레톤 로딩 화면을 표시합니다.
- 선택한 난이도에 문제가 없으면 빈 상태를 표시합니다.
- 요청 실패 시 안전한 오류 메시지와 `다시 시도` 버튼을 표시합니다.
- 답안을 수정한 뒤 문제·모드·언어를 바꾸면 답안 폐기 확인 대화상자를 표시합니다.
- 수정 중 페이지를 닫거나 새로 고치면 브라우저의 이탈 경고를 요청합니다.

## 답안 제출

- 로컬에서도 브라우저가 같은 출처의 `POST /api/submit`으로 답안을 제출합니다.
- 중수·고수 코드 답안은 Flask API가 공개·비공개 테스트를 Judge0 batch 실행으로 채점합니다.
- 초보 의사코드는 문제별 루브릭과 함께 Hugging Face로 보내며, 로컬 `.env` 또는 `.env.local`에 `HF_TOKEN`이 필요합니다.
- 비공개 입력·정답은 응답에 포함하지 않고 통과 개수와 안전한 오류 요약만 표시합니다.

## 로컬 실행

```powershell
pnpm install
pnpm setup:python
pnpm dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 엽니다. `pnpm dev`는 Next.js와 Flask API를 함께 실행합니다.

## 검증

```powershell
pnpm lint
pnpm test
pnpm build
```

브라우저 검증 범위는 데스크톱 Monaco 입력, 문제·모드·언어 전환, 미제출 경고의 취소/확인, 답안 제출과 채점 결과, 오류·재시도 화면, 390px 모바일 단일 열과 대체 코드 편집기입니다.
