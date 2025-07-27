# Trading CORE API 사용 가이드 📊

## 🚀 시스템 현재 상태 
- **보안 시스템**: 완전 제거됨 (JWT, Rate Limiting, CORS 등)
- **인증**: 없음 - 모든 API 자유롭게 호출 가능
- **캐싱**: Redis 기반 응답 캐싱 (5-60초 TTL)
- **데이터 소스**: 
  - Redis (실시간 1분봉 최신 1개)
  - PostgreSQL (과거 데이터 + 기술적 지표)
  - Binance API (실시간 연동)
- **신호 생성**: 정상 작동 중 (다중 시간대 분석)
- **포지션 모니터링**: 백그라운드 실행 중
- **스케줄러**: 자동 신호 생성 활성화됨

## 기본 정보
- **Base URL**: `http://localhost:8000`
- **응답 형식**: JSON
- **인증**: 없음 (보안 시스템 제거됨)
- **Content-Type**: `application/json`
- **마지막 업데이트**: 2025년 7월 27일

## 공통 응답 형식
모든 API는 다음과 같은 형식으로 응답합니다:
```json
{
  "success": true,
  "message": "응답 메시지",
  "timestamp": "2025-07-27T22:00:00.000000",
  "data": {}
}
```

---

## 1. 기본 시스템 API

### 시스템 상태 확인
```javascript
// 전체 시스템 헬스체크
fetch('http://localhost:8000/health')
  .then(response => response.json())
  .then(data => console.log(data));

// 응답 예시:
{
  "success": true,
  "message": "모든 서비스가 정상적으로 작동 중입니다.",
  "data": {
    "status": "healthy",
    "redis": "connected",
    "database": "connected"
  }
}
```

### API 루트 정보
```javascript
fetch('http://localhost:8000/')
  .then(response => response.json())
  .then(data => console.log(data));
```

---

## 2. 데이터 조회 API (`/api/v1/data`)

### 실시간 K-라인 데이터 (개선됨! 🎉)
```javascript
// 실시간 최신 1개 데이터 (Redis에서 실시간 데이터)
fetch('http://localhost:8000/api/v1/data/realtime/klines?symbol=BTCUSDT&interval=1m&limit=1')
  .then(response => response.json())
  .then(data => {
    console.log('실시간 데이터:', data.data[0]);
    // 출력 예시: {"t":1753623360000,"T":1753623419999,"s":"BTCUSDT","o":"118114.80","c":"118114.80","h":"118114.80","l":"118114.70","v":"12.262","x":true}
  });

// 여러 개 데이터 요청 시 DB에서 기술적 지표 포함 데이터
fetch('http://localhost:8000/api/v1/data/realtime/klines?symbol=BTCUSDT&interval=1m&limit=10')
  .then(response => response.json())
  .then(data => {
    console.log('DB 데이터 (Binance 형식):', data.data);
    // 여러 개 캔들 데이터가 Binance API 형식으로 반환됨
  });

// 다른 시간대 (Binance API 직접 호출)
fetch('http://localhost:8000/api/v1/data/realtime/klines?symbol=ETHUSDT&interval=5m&limit=50')
  .then(response => response.json())
  .then(data => console.log('5분 차트:', data.data));
```

### 실시간 거래 데이터
```javascript
// 최근 거래 내역
fetch('http://localhost:8000/api/v1/data/realtime/trades?symbol=BTCUSDT&limit=50')
  .then(response => response.json())
  .then(data => console.log(data));
```

### 실시간 오더북
```javascript
// 호가창 데이터
fetch('http://localhost:8000/api/v1/data/realtime/order-book?symbol=BTCUSDT&limit=20')
  .then(response => response.json())
  .then(data => console.log(data));
```

### 기술적 지표가 포함된 K-라인 데이터 (DB에서)
```javascript
// ATR, EMA, SMA, RSI, MACD 등 포함
fetch('http://localhost:8000/api/v1/data/klines?symbol=BTCUSDT&limit=100')
  .then(response => response.json())
  .then(data => {
    // data.data 배열에서 각 캔들 정보 + 기술적 지표
    data.data.forEach(candle => {
      console.log(`가격: ${candle.close}, RSI: ${candle.rsi_14}, ATR: ${candle.atr}`);
    });
  });
```

### 펀딩비 데이터
```javascript
fetch('http://localhost:8000/api/v1/data/historical/funding-rates?symbol=BTCUSDT&limit=24')
  .then(response => response.json())
  .then(data => console.log(data));
```

### 미결제 약정 데이터
```javascript
fetch('http://localhost:8000/api/v1/data/historical/open-interest?symbol=BTCUSDT&limit=24')
  .then(response => response.json())
  .then(data => console.log(data));
```

### 시장 정보
```javascript
// 특정 심볼 정보
fetch('http://localhost:8000/api/v1/data/market-info?symbol=BTCUSDT')

// 전체 거래소 정보
fetch('http://localhost:8000/api/v1/data/market-info')
```

---

## 3. 거래 신호 API (`/api/v1/signals`)

### 최신 신호 조회
```javascript
// 기본 (BTCUSDT)
fetch('http://localhost:8000/api/v1/signals/latest')
  .then(response => response.json())
  .then(data => {
    const signal = data.data;
    console.log(`신호: ${signal.signal}, 신뢰도: ${signal.confidence_score}`);
  });

// 특정 심볼
fetch('http://localhost:8000/api/v1/signals/latest?symbol=ETHUSDT')
```

### 통합 신호 조회
```javascript
fetch('http://localhost:8000/api/v1/signals/combined/BTCUSDT')
  .then(response => response.json())
  .then(data => console.log(data));
```

### 신호 생성 (POST)
```javascript
fetch('http://localhost:8000/api/v1/signals/generate/BTCUSDT', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

### 신호 성과 분석
```javascript
fetch('http://localhost:8000/api/v1/signals/performance')
  .then(response => response.json())
  .then(data => {
    const perf = data.data;
    console.log(`승률: ${perf.win_rate}%, 연속 손실: ${perf.consecutive_losses}`);
  });
```

### 신호 기록 조회
```javascript
fetch('http://localhost:8000/api/v1/signals/history?limit=50')
  .then(response => response.json())
  .then(data => console.log(data));
```

---

## 4. 주문/포지션 관리 API (`/api/v1/orders`)

### 현재 포지션 조회
```javascript
fetch('http://localhost:8000/api/v1/orders/positions')
  .then(response => response.json())
  .then(data => {
    const positions = data.data.data.positions;
    positions.forEach(pos => {
      console.log(`심볼: ${pos.symbol}, 사이즈: ${pos.size}, PnL: ${pos.unrealized_pnl}`);
    });
  });
```

### 계정 정보 조회
```javascript
// 선물 계정
fetch('http://localhost:8000/api/v1/orders/account/futures')
  .then(response => response.json())
  .then(data => console.log(data));

// 현물 계정
fetch('http://localhost:8000/api/v1/orders/account/spot')
```

### 오픈 주문 조회
```javascript
// 모든 오픈 주문
fetch('http://localhost:8000/api/v1/orders/open')

// 특정 심볼의 오픈 주문
fetch('http://localhost:8000/api/v1/orders/open?symbol=BTCUSDT')
```

### 포지션 강제 종료
```javascript
// 특정 포지션 종료
fetch('http://localhost:8000/api/v1/orders/positions/BTCUSDT', {
  method: 'DELETE'
})
.then(response => response.json())
.then(data => console.log(data));

// 모든 포지션 종료
fetch('http://localhost:8000/api/v1/orders/positions/all', {
  method: 'DELETE'
})
```

### 신호 처리 (POST)
```javascript
const signal = {
  symbol: "BTCUSDT",
  signal: "BUY",
  stop_loss_price: 95000,
  take_profit_price: 105000,
  position_size: 0.1,
  confidence_score: 0.8
};

fetch('http://localhost:8000/api/v1/orders/process-signal', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(signal)
})
.then(response => response.json())
.then(data => console.log(data));
```

### 자동 거래 제어
```javascript
// 자동 거래 활성화
fetch('http://localhost:8000/api/v1/orders/auto-trading/toggle?enabled=true', {
  method: 'POST'
})

// 자동 거래 상태 조회
fetch('http://localhost:8000/api/v1/orders/auto-trading/status')
```

---

## 5. 거래 설정 API (`/api/v1/settings`)

### 현재 설정 조회
```javascript
fetch('http://localhost:8000/api/v1/settings/trading')
  .then(response => response.json())
  .then(data => {
    const settings = data;
    console.log(`레버리지: ${settings.LEVERAGE}x`);
    console.log(`리스크: ${settings.RISK_PER_TRADE * 100}%`);
    console.log(`자동거래: ${settings.AUTO_TRADING_ENABLED}`);
  });
```

### 설정 업데이트 (POST)
```javascript
const newSettings = {
  TIMEFRAME: "5m",
  LEVERAGE: 20,
  RISK_PER_TRADE: 0.03,
  ACCOUNT_BALANCE: 15000.0,
  AUTO_TRADING_ENABLED: true,
  ATR_MULTIPLIER: 2.0,
  TP_RATIO: 2.0,
  VOLUME_SPIKE_THRESHOLD: 1.8,
  PRICE_MOMENTUM_THRESHOLD: 0.005,
  MIN_SIGNAL_INTERVAL_MINUTES: 10,
  MAX_CONSECUTIVE_LOSSES: 5,
  ACTIVE_HOURS: [[9, 24], [0, 2]]
};

fetch('http://localhost:8000/api/v1/settings/trading', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(newSettings)
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## 6. 로그 모니터링 API (`/api/v1/logs`)

### 최근 로그 조회
```javascript
fetch('http://localhost:8000/api/v1/logs/recent?limit=100')
  .then(response => response.json())
  .then(data => {
    data.logs.forEach(log => {
      console.log(`[${log.level}] ${log.message}`);
    });
  });
```

### 실시간 로그 WebSocket 연결
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/logs/ws');

ws.onopen = function() {
  console.log('로그 스트림 연결됨');
};

ws.onmessage = function(event) {
  const logEntry = JSON.parse(event.data);
  console.log(`[${logEntry.level}] ${logEntry.message}`);
  
  // 로그를 화면에 표시하는 로직
  displayLog(logEntry);
};

ws.onclose = function() {
  console.log('로그 스트림 연결 종료');
};
```

---

## 7. 프론트엔드 사용 예시

### React 컴포넌트 예시
```jsx
import React, { useState, useEffect } from 'react';

function TradingDashboard() {
  const [positions, setPositions] = useState([]);
  const [signals, setSignals] = useState(null);
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    // 초기 데이터 로드
    loadPositions();
    loadLatestSignal();
    loadSettings();
    
    // 5초마다 갱신
    const interval = setInterval(() => {
      loadPositions();
      loadLatestSignal();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const loadPositions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/orders/positions');
      const data = await response.json();
      if (data.success) {
        setPositions(data.data.data.positions);
      }
    } catch (error) {
      console.error('포지션 로드 실패:', error);
    }
  };

  const loadLatestSignal = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/signals/latest');
      const data = await response.json();
      if (data.success) {
        setSignals(data.data);
      }
    } catch (error) {
      console.error('신호 로드 실패:', error);
    }
  };

  const loadSettings = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/settings/trading');
      const data = await response.json();
      setSettings(data);
    } catch (error) {
      console.error('설정 로드 실패:', error);
    }
  };

  return (
    <div>
      <h1>Trading Dashboard</h1>
      
      {/* 신호 표시 */}
      {signals && (
        <div>
          <h2>최신 신호</h2>
          <p>심볼: {signals.symbol}</p>
          <p>신호: {signals.signal}</p>
          <p>신뢰도: {signals.confidence_score}</p>
        </div>
      )}
      
      {/* 포지션 표시 */}
      <div>
        <h2>현재 포지션</h2>
        {positions.length === 0 ? (
          <p>활성 포지션이 없습니다.</p>
        ) : (
          positions.map(pos => (
            <div key={pos.symbol}>
              <p>{pos.symbol}: {pos.size} ({pos.side})</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

### Vue.js 컴포넌트 예시  
```vue
<template>
  <div>
    <h1>Trading Dashboard</h1>
    
    <div v-if="signal">
      <h2>최신 신호</h2>
      <p>{{ signal.symbol }}: {{ signal.signal }}</p>
    </div>
    
    <div>
      <h2>K-라인 차트</h2>
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      signal: null,
      klines: []
    };
  },
  
  async mounted() {
    await this.loadData();
    setInterval(this.loadData, 5000);
  },
  
  methods: {
    async loadData() {
      // 신호 로드
      const signalResponse = await fetch('http://localhost:8000/api/v1/signals/latest');
      const signalData = await signalResponse.json();
      if (signalData.success) {
        this.signal = signalData.data;
      }
      
      // K-라인 데이터 로드
      const klinesResponse = await fetch('http://localhost:8000/api/v1/data/klines?symbol=BTCUSDT&limit=100');
      const klinesData = await klinesResponse.json();
      if (klinesData.success) {
        this.klines = klinesData.data;
        this.updateChart();
      }
    },
    
    updateChart() {
      // 차트 업데이트 로직
    }
  }
};
</script>
```

---

## 8. 에러 처리

API 요청 실패 시 공통 에러 응답:
```json
{
  "success": false,
  "message": "에러 메시지",
  "timestamp": "2025-01-27T12:00:00.000000",
  "error_code": "ERROR_CODE"
}
```

### JavaScript 에러 처리 예시
```javascript
async function apiCall(url, options = {}) {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || '알 수 없는 오류가 발생했습니다.');
    }
    
    return data.data;
  } catch (error) {
    console.error('API 호출 실패:', error);
    throw error;
  }
}

// 사용 예시
try {
  const positions = await apiCall('http://localhost:8000/api/v1/orders/positions');
  console.log(positions);
} catch (error) {
  alert('포지션 조회 실패: ' + error.message);
}
```

이 가이드를 참고하여 프론트엔드에서 Trading CORE API를 효율적으로 활용하실 수 있습니다.

---

## 📈 최신 개선사항 (2025년 7월 28일)

1. **응답 캐싱 구현**: Redis 기반 자동 캐싱으로 반복 요청 최적화
   - 실시간 K-라인: 10초 캐싱
   - 거래 데이터: 5초 캐싱  
   - 포지션 정보: 15초 캐싱
   - 계정 정보: 30초 캐싱

2. **로깅 최적화**: 불필요한 INFO 로그를 DEBUG로 변경하여 로그 스팸 감소

3. **Binance API 보호**: IP 차단 시 캐시 데이터로 Fallback 처리

4. **성능 향상**: 동일한 요청에 대해 캐시된 응답으로 즉시 처리

💡 **캐싱 확인**: 응답 헤더의 `x-cache: HIT/MISS`로 캐시 상태 확인 가능
