# Trading_CORE

## 개요
Trading_CORE는 암호화폐 자동거래를 위한 종합적인 백엔드 시스템입니다. FastAPI를 기반으로 구축되었으며, Binance API와 통합되어 실시간 데이터 처리, 거래 신호 생성, 주문 관리 등의 기능을 제공합니다.

## 주요 기능
- 실시간 시장 데이터 수집 및 처리
- 자동 거래 신호 생성 및 분석
- 포지션 관리 및 자동 거래 실행
- 계정 정보 및 거래 내역 조회
- RESTful API 제공

## 기술 스택
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Trading Platform**: Binance API
- **Language**: Python 3.12+

## API 문서

### 시스템 API

#### 1. 루트 엔드포인트
```
GET /
```
- **설명**: API 루트 엔드포인트, 시스템 상태 확인
- **응답**: 
  ```json
  {
    "success": true,
    "data": {
      "name": "Trading CORE API",
      "version": "1.0.0",
      "status": "healthy"
    },
    "message": "Trading CORE API가 정상적으로 작동 중입니다."
  }
  ```

#### 2. 헬스체크
```
GET /health
```
- **설명**: 시스템 헬스체크, Redis 및 Database 연결 상태 확인
- **응답**:
  ```json
  {
    "success": true,
    "data": {
      "status": "healthy",
      "redis": "connected",
      "database": "connected"
    },
    "message": "모든 서비스가 정상적으로 작동 중입니다."
  }
  ```

### 주문 관리 API (`/api/v1/orders`)

#### 1. 서비스 상태 확인
```
GET /api/v1/orders/health
```
- **설명**: 주문 서비스 상태 확인
- **응답**: 서비스 상태 정보

#### 2. 포지션 관리
```
GET /api/v1/orders/positions
```
- **설명**: 현재 활성 포지션 조회
- **응답**: 활성 포지션 목록

```
DELETE /api/v1/orders/positions/{symbol}
```
- **설명**: 특정 포지션 강제 종료
- **파라미터**: symbol (거래 심볼)
- **응답**: 포지션 종료 결과

```
DELETE /api/v1/orders/positions/all
```
- **설명**: 모든 포지션 강제 종료
- **응답**: 전체 포지션 종료 결과

#### 3. 계정 정보
```
GET /api/v1/orders/account/futures
```
- **설명**: 선물 계정 정보 조회
- **응답**: 선물 계정 잔고 및 마진 정보

```
GET /api/v1/orders/account/spot
```
- **설명**: 현물 계정 정보 조회
- **응답**: 현물 계정 잔고 정보

#### 4. 자동 거래 제어
```
POST /api/v1/orders/auto-trading/toggle
```
- **설명**: 자동 거래 토글 (활성화/비활성화)
- **요청**: `enabled` 쿼리 파라미터 (boolean)
- **응답**: 자동 거래 상태

```
GET /api/v1/orders/auto-trading/status
```
- **설명**: 자동 거래 상태 조회
- **응답**: 현재 자동 거래 상태

#### 5. 주문 실행 및 관리
```
POST /api/v1/orders/process-signal
```
- **설명**: 거래 신호 처리 및 주문 실행
- **요청**: TradingSignal 객체
- **응답**: 신호 처리 결과

```
POST /api/v1/orders/close/{symbol}
```
- **설명**: 특정 포지션 수동 종료
- **파라미터**: symbol (거래 심볼)
- **쿼리 파라미터**: reason (종료 사유, 기본값: "MANUAL_CLOSE")
- **응답**: 포지션 종료 결과

#### 6. 주문 및 거래소 정보
```
GET /api/v1/orders/open
```
- **설명**: 오픈된 주문 조회
- **쿼리 파라미터**: symbol (옵션)
- **응답**: 오픈 주문 목록

```
GET /api/v1/orders/exchange-info
```
- **설명**: 거래소 규칙 정보 조회
- **응답**: 심볼별 거래 규칙 (최소 주문 수량, 가격/수량 정밀도 등)

### 신호 관리 API (`/api/v1/signals`)

#### 1. 서비스 상태 확인
```
GET /api/v1/signals/health
```
- **설명**: 신호 서비스 상태 확인
- **응답**: 서비스 상태 정보

#### 2. 신호 조회
```
GET /api/v1/signals/latest
```
- **설명**: 최신 신호 조회
- **쿼리 파라미터**: symbol (옵션)
- **응답**: 최신 신호 정보

```
GET /api/v1/signals/combined/{symbol}
```
- **설명**: 특정 심볼의 통합 신호 조회
- **파라미터**: symbol (거래 심볼)
- **응답**: 통합 신호 정보

```
GET /api/v1/signals/cached
```
- **설명**: 캐시된 신호 조회
- **쿼리 파라미터**: symbol (옵션)
- **응답**: 캐시된 신호 정보

#### 3. 신호 생성
```
POST /api/v1/signals/generate/{symbol}
```
- **설명**: 특정 심볼의 새로운 거래 신호 생성
- **파라미터**: symbol (거래 심볼)
- **응답**: 생성된 신호 정보

#### 4. 신호 성과 분석
```
GET /api/v1/signals/performance
```
- **설명**: 신호 성과 분석
- **쿼리 파라미터**: 
  - symbol (옵션): 거래 심볼
  - days (옵션): 분석 기간 (기본값: 30일)
- **응답**: 성과 분석 결과

#### 5. 신호 이력
```
GET /api/v1/signals/history
```
- **설명**: 신호 이력 조회
- **쿼리 파라미터**: 
  - symbol (옵션): 거래 심볼
  - limit (옵션): 결과 개수 제한 (기본값: 100)
- **응답**: 신호 이력 목록

### 데이터 관리 API (`/api/v1/data`)

#### 1. 실시간 데이터
```
GET /api/v1/data/realtime/klines
```
- **설명**: 실시간 K-라인 데이터 조회
- **쿼리 파라미터**: 
  - symbol: 거래 심볼 (필수)
  - interval: 시간 간격 (기본값: "1m")
  - limit: 결과 개수 제한 (기본값: 1)
- **응답**: K-라인 데이터 목록

```
GET /api/v1/data/realtime/trades
```
- **설명**: 실시간 거래 데이터 조회
- **쿼리 파라미터**: 
  - symbol: 거래 심볼 (필수)
  - limit: 결과 개수 제한 (기본값: 50)
- **응답**: 실시간 거래 데이터

```
GET /api/v1/data/realtime/order-book
```
- **설명**: 실시간 오더북 조회
- **쿼리 파라미터**: 
  - symbol: 거래 심볼 (필수)
  - limit: 결과 개수 제한 (기본값: 20)
- **응답**: 오더북 데이터

#### 2. 과거 데이터
```
GET /api/v1/data/klines
```
- **설명**: 과거 K-라인 데이터 조회
- **쿼리 파라미터**: 
  - symbol: 거래 심볼 (필수)
  - limit: 결과 개수 제한 (기본값: 100)
- **응답**: 과거 K-라인 데이터

```
GET /api/v1/data/historical/trades
```
- **설명**: 과거 거래 데이터 조회
- **쿼리 파라미터**: 
  - symbol: 거래 심볼 (필수)
  - limit: 결과 개수 제한 (기본값: 100)
- **응답**: 과거 거래 데이터

#### 3. 시장 정보
```
GET /api/v1/data/market-info
```
- **설명**: 시장 정보 및 통계 조회
- **쿼리 파라미터**: 
  - symbol (옵션): 거래 심볼
- **응답**: 시장 정보 및 통계

### 로그 관리 API (`/api/v1/logs`)

#### 1. 로그 조회
```
GET /api/v1/logs/recent
```
- **설명**: 최근 로그 조회
- **쿼리 파라미터**: 
  - limit (옵션): 결과 개수 제한 (기본값: 100)
- **응답**: 최근 로그 목록

#### 2. 실시간 로그 스트림
```
WebSocket /api/v1/logs/ws
```
- **설명**: 실시간 로그 스트리밍
- **프로토콜**: WebSocket
- **응답**: 실시간 로그 메시지

### API 버전 관리

모든 API는 v1 버전으로 통합되어 제공됩니다:
- **통합 API**: `/api/v1/orders/...`, `/api/v1/signals/...`, `/api/v1/data/...`, `/api/v1/logs/...`

### API 통계

현재 구현된 API 엔드포인트:
- **시스템 API**: 2개 (루트, 헬스체크)
- **주문 관리 API**: 10개 (포지션, 계정, 자동거래, 주문 실행 등)
- **신호 관리 API**: 7개 (신호 생성, 조회, 성과 분석, 이력 등)
- **데이터 관리 API**: 6개 (실시간/과거 데이터, 시장 정보 등)
- **로그 관리 API**: 2개 (로그 조회, 실시간 스트리밍)

**총 27개의 API 엔드포인트 제공**

### 응답 형식

모든 API는 다음과 같은 표준 응답 형식을 사용합니다:

```json
{
  "success": true,
  "data": { /* 응답 데이터 */ },
  "message": "요청이 성공적으로 처리되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

에러 발생 시:
```json
{
  "success": false,
  "message": "에러 메시지",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 인증 및 보안

- API 키 기반 인증 (Binance API 키 사용)
- HTTPS 통신 권장
- 요청 제한 및 스로틀링 적용

### 사용 예시

#### 1. 계정 정보 조회
```bash
curl -X GET "http://localhost:8000/api/v1/orders/account/futures" \
  -H "Accept: application/json"
```

#### 2. 실시간 K-라인 데이터 조회
```bash
curl -X GET "http://localhost:8000/api/v1/data/realtime/klines?symbol=BTCUSDT&interval=1m&limit=100" \
  -H "Accept: application/json"
```

#### 3. 거래 신호 생성
```bash
curl -X POST "http://localhost:8000/api/v1/signals/generate/BTCUSDT" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json"
```

#### 4. 실시간 로그 스트림 (WebSocket)
```bash
# WebSocket 연결 예시 (JavaScript)
const ws = new WebSocket('ws://localhost:8000/api/v1/logs/ws');
ws.onmessage = function(event) {
  const logData = JSON.parse(event.data);
  console.log('실시간 로그:', logData);
};
```

#### 5. 자동거래 토글
```bash
curl -X POST "http://localhost:8000/api/v1/orders/auto-trading/toggle?enabled=true" \
  -H "Accept: application/json"
```

#### 6. 포지션 수동 종료
```bash
curl -X DELETE "http://localhost:8000/api/v1/orders/positions/BTCUSDT" \
  -H "Accept: application/json"
```

#### 7. 최신 신호 조회
```bash
curl -X GET "http://localhost:8000/api/v1/signals/latest?symbol=BTCUSDT" \
  -H "Accept: application/json"
```

#### 8. 현재 포지션 조회
```bash
curl -X GET "http://localhost:8000/api/v1/orders/positions" \
  -H "Accept: application/json"
```

#### 9. 서비스 상태 확인
```bash
curl -X GET "http://localhost:8000/api/v1/orders/health" \
  -H "Accept: application/json"
```

#### 10. 오더북 조회
```bash
curl -X GET "http://localhost:8000/api/v1/data/realtime/order-book?symbol=BTCUSDT&limit=20" \
  -H "Accept: application/json"
```

---

## 설치 및 실행

### 요구사항
- Python 3.12+
- PostgreSQL
- Redis
- Binance API 키

### 설치
```bash
# 의존성 관리 도구 설치
pip install pip-tools

# 의존성 컴파일 및 설치
pip-compile requirements.in
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에 필요한 설정 입력

# 데이터베이스 마이그레이션 (Alembic 사용하는 경우)
# alembic upgrade head

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 환경 변수
`.env` 파일에 다음 환경 변수를 설정해야 합니다.

```env
# PostgreSQL
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_core

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Binance API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret_key
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_secret_key

# Trading Symbols
TRADING_SYMBOLS=BTCUSDT,ETHUSDT
```

## 라이선스
MIT License