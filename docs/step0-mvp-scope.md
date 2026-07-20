# Step 0 MVP 범위 확정안

## 확정 기술 스택

- 프론트엔드: Next.js App Router, TypeScript, React, Monaco Editor
- 백엔드: Python Flask를 Vercel Python Function으로 배포
- 코드 실행: Judge0 CE 호환 API 우선, 공급자 어댑터로 격리
- AI 평가: Hugging Face Inference Providers, strict JSON Schema
- 문제 제공: 실시간 생성이 아닌 저장된 사전 검증 문제
- 초기 데이터: 저장소의 버전 관리되는 JSON으로 시작하고, 운영 중 편집·통계가 필요할 때 데이터베이스로 이전

## MVP 포함

- 비로그인 단일 사용자 세션
- 초짜·중짜·타짜 세 모드
- Python 3 및 C++
- 문제 조회, 답안 제출, 채점 결과, 타이머, 시간 종료 자동 제출
- 초짜의 루브릭 기반 의사코드 평가와 짧은 개선 피드백
- 중짜·타짜의 공개/비공개 테스트 채점
- 최소 6개 검증 문제
- Vercel Preview/Production 배포와 추적 ID 기반 오류 로그

## MVP 제외

- 로그인, 영구 학습 기록, 랭킹, 결제, 커뮤니티
- 실시간 AI 문제 생성
- 자체 Judge0/Piston 운영
- Python/C++ 외 언어
- 정교한 AI 튜터 대화와 정답 전체 생성
- 대규모 문제 관리 CMS

## 비기능 기준

- 정상 문제 조회 응답 목표: 1초 이내
- 샌드박스 채점 앱 타임아웃 목표: 15초 이내
- AI 평가 앱 타임아웃 목표: 15초 이내
- 제출 코드 크기: 64 KiB 이하
- 의사코드 입력: 8,000자 이하
- 비공개 테스트와 정답은 서버에서만 접근
- 외부 API 키는 서버 환경 변수에만 저장

## Step 0 승인 결과

- Judge0 CE Python/C++ 실행: 각각 3/3 성공
- Hugging Face strict JSON Schema: 3/3 성공
- AI 모델: `openai/gpt-oss-120b:groq`
- 앱 타임아웃 목표: 외부 호출당 15초
- AI 출력 상한: 요청당 300 tokens
- MVP 트래픽 보호: 세션별 제출 빈도 제한과 일일 사용량 관측을 Step 5~7에서 구현

공개 서비스 전에는 외부 공급자의 이용 약관과 예상 트래픽을 다시 검토한다.
