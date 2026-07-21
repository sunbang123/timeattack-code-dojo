# Step 3 문제 조회 API

## 요청

```http
GET /api/problem?difficulty=easy&mode=intermediate&language=python
```

필수 쿼리 파라미터:

- `difficulty`: `easy`, `medium`, `hard`
- `mode`: `beginner`, `intermediate`, `expert`
- `language`: `python`, `cpp`

선택 파라미터 `problem_id`로 같은 난이도 안의 특정 문제를 지정할 수 있다. 생략하면 `problem_bank/manifest.json`에서 해당 난이도의 첫 문제를 안정적으로 선택한다. 알 수 없는 파라미터, 중복 파라미터, 빈 값은 `400`으로 거절한다.

## 성공 응답

```json
{
  "bank_version": 1,
  "problem": {
    "id": "sum-two-numbers",
    "version": 1,
    "title": "두 수의 합",
    "difficulty": "easy",
    "mode": "intermediate",
    "language": "python",
    "time_limit_seconds": 600,
    "answer_format": "code",
    "starter_code": "..."
  }
}
```

문제 설명, 제약, 공개 예시와 태그도 함께 반환한다. 모드별 필드는 다음처럼 제한한다.

- `beginner`: `prompt`만 추가
- `intermediate`: 요청 언어의 TODO 스켈레톤을 `starter_code`로 추가
- `expert`: 요청 언어의 최소 템플릿을 `starter_code`로 추가

전체 `modes`, 다른 언어의 코드, 기준 정답, 루브릭, 비공개 테스트는 반환하지 않는다.

## 오류 응답

```json
{
  "error": {
    "code": 400,
    "message": "Invalid language; expected one of: python, cpp",
    "request_id": "..."
  }
}
```

- `400`: 필수·허용 값·중복·알 수 없는 파라미터 오류
- `404`: `problem_id`가 없거나 요청 난이도와 일치하지 않음
- `500`: 문제은행 파일 누락 또는 내부 데이터 불일치

모든 응답은 `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Request-ID` 헤더를 유지한다.

## 검증

```powershell
pnpm test:api
```

테스트는 세 모드, 두 언어, 세 난이도, 특정 문제 선택, 오류 형식과 민감 필드 비노출을 확인한다.
