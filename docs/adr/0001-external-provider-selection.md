# ADR-0001: MVP 외부 실행·AI 공급자 선택

- 상태: 승인
- 결정일: 2026-07-20
- 대상: Step 0

## 결정

1. 코드 실행의 1순위는 Judge0 CE API로 한다.
2. 요청은 `wait=true`에 의존하지 않고 제출 생성 후 토큰을 짧게 폴링한다.
3. Piston은 MVP의 기본 공개 공급자로 사용하지 않는다. 자체 호스팅이 필요해지는 경우의 대체 어댑터로만 유지한다.
4. 의사코드 평가는 Hugging Face Inference Providers의 OpenAI 호환 Chat Completion API를 사용한다.
5. AI 응답은 JSON Schema의 strict 모드로 `passed`, `score`, `feedback`, `missing_steps`를 강제한다.
6. 초기 검증 모델은 현재 Inference Providers 지원 목록에 있고 Groq 경로를 명시할 수 있는 `openai/gpt-oss-120b:groq`로 한다. 실제 품질·비용 측정 후 모델은 환경 변수로 교체할 수 있어야 한다.

## 근거

- Judge0 CE는 Python/C++ 실행, 실행 시간·메모리 제한, 비동기 제출 토큰과 상태 조회를 공식 API로 제공한다.
- Piston 공개 API는 2026-02-15부터 인증 토큰이 필요하며 개인·포트폴리오 프로젝트에는 발급이 제한적이라고 공식 저장소에 명시되어 있다.
- Hugging Face Chat Completion은 OpenAI 호환 엔드포인트와 strict JSON Schema 응답을 제공한다. 문제별 평가 루브릭과 함께 사용하면 파싱 실패를 줄일 수 있다.
- Vercel Hobby의 현재 Python/Node.js 함수 최대 실행 시간은 Fluid compute 기준 300초다. 다만 학습 UX와 장애 격리를 위해 코드 실행·AI 평가는 각각 약 8~15초의 애플리케이션 타임아웃을 사용한다.

## 운영 규칙

- 모든 비밀 키는 서버 환경 변수에서만 읽고 응답·로그·클라이언트 번들에 포함하지 않는다.
- 외부 공급자 응답은 내부 공통 결과 형식으로 변환한다.
- 오류 출력은 길이를 제한하고 비공개 테스트 입력과 정답을 제거한다.
- 공급자 재시도는 네트워크 오류에만 최대 1회 적용하며 사용자 코드 오류에는 적용하지 않는다.
- Judge0의 언어 ID는 고정값이 아니라 `/languages/` 결과에서 버전을 확인해 매핑한다.

## 대안

- Piston 공개 API: 인증 정책 때문에 기본안에서 제외한다.
- Piston 자체 호스팅: 제어권은 높지만 Docker·런타임 관리가 필요하므로 MVP 이후로 미룬다.
- Judge0 자체 호스팅: 사용량이나 보안 요구가 관리형/공개 인스턴스를 넘을 때 검토한다.
- Hugging Face 일반 JSON mode: strict schema를 지원하지 않는 모델의 임시 대안으로만 사용한다.

## 최종 승인 조건

- [x] Judge0 Python/C++ 샘플이 각각 3회 연속 통과한다.
- [x] Hugging Face 의사코드 평가가 JSON Schema 검증을 3회 연속 통과한다.
- [x] 측정한 지연 시간과 실패 응답이 이 ADR에 추가된다.

## 2026-07-20 라이브 PoC 결과

- 로컬 검증 코드 단위 테스트: 4/4 통과
- Judge0 CE: 실행 환경에서 `/languages/` 호출 시 Cloudflare Error 1010, HTTP 403 반환
- Judge0 조치: 응답이 재시도를 금지하므로 동일 엔드포인트의 반복 호출을 중단함
- Piston: 공개 API 토큰이 없어 실행하지 않음
- Hugging Face: `HF_TOKEN`이 설정되지 않아 실행하지 않음
- 상세 결과: `artifacts/step0-results.json`

후속 검증에서 토큰 인증은 통과했으나 기존 후보 `Qwen/Qwen3-32B:cerebras`가 공급자에서 폐기된 것을 확인했다. 후보를 `openai/gpt-oss-120b:groq`로 교체했다.

초기 요청은 Python 기본 HTTP 서명이 Cloudflare에서 차단되었다. 프로젝트 전용 User-Agent를 명시한 뒤 정상적인 API 인증과 실행이 가능해졌다.

## 최종 라이브 결과

### Judge0 CE

- 엔드포인트: `https://ce.judge0.com`
- 인증: 현재 PoC에서는 별도 토큰 없이 성공
- Python 런타임: Python 3.14.0, 3/3 Accepted, 왕복 지연 2,817~2,868ms
- C++ 런타임: GCC 14.1.0, 3/3 Accepted, 왕복 지연 2,534~2,823ms
- 결과 파일: `artifacts/step0-judge0-results.json`

### Hugging Face Inference Providers

- 모델/공급자: `openai/gpt-oss-120b:groq`
- strict JSON Schema: 3/3 통과
- 평가 결과: 3회 모두 passed=true, score=100
- 왕복 지연: 728~854ms
- 결과 파일: `artifacts/step0-huggingface-results.json`

### Piston

- 공개 API 토큰 정책 때문에 라이브 비교에서 제외
- Judge0 장애 시 자체 호스팅 대안으로만 유지

## 공식 자료

- [Judge0 CE API](https://ce.judge0.com/docs)
- [Piston 공식 저장소](https://github.com/engineer-man/piston)
- [Hugging Face Chat Completion](https://huggingface.co/docs/inference-providers/en/tasks/chat-completion)
- [Hugging Face Structured Outputs](https://huggingface.co/docs/huggingface_hub/en/guides/inference)
- [Vercel Functions 제한](https://vercel.com/docs/functions/limitations)
