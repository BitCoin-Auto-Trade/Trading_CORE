# Trading CORE API 사용 가이드 📊

## 🚀 시스템 현재 상태 (최신 업데이트: 2025년 7월 28일)
- **아키텍처**: FastAPI 완전 리팩토링 완료 ✨
- **미들웨어 시스템**: 계층화된 미들웨어 (에러 핸들링, 로깅, 캐싱, CORS)
- **캐싱**: Redis 기반 응답 캐싱 (엔드포인트별 최적화된 TTL)
  - K-라인: 5초, 거래내역: 10초, 포지션: 30초, 계정정보: 60초
- **성능**: 캐시 HIT 시 밀리초 단위 응답 (X-Cache 헤더로 확인 가능)
- **에러 처리**: 전역 에러 핸들링으로 안정성 강화
- **로깅**: 요청/응답 자동 로깅 + 성능 측정 (X-Process-Time 헤더)
- **자동거래**: 기본값 OFF (안전을 위한 설정)
- **데이터 소스**: 
  - Redis (실시간 1분봉 최신 1개)
  - PostgreSQL (과거 데이터 + 기술적 지표)
  - Binance API (실시간 연동 + 폴백 메커니즘)
- **신호 생성**: 정상 작동 중 (다중 시간대 분석)
- **포지션 모니터링**: 백그라운드 실행 중 (에러 핸들링 강화)
- **스케줄러**: 자동 신호 생성 활성화됨

## 기본 정보
- **Base URL**: `http://localhost:8000`
- **응답 형식**: JSON
- **인증**: 없음 (개발 환경)
- **Content-Type**: `application/json`
- **CORS**: 모든 오리진 허용 (개발 환경)
- **마지막 업데이트**: 2025년 7월 28일

## 📊 성능 모니터링 헤더
모든 응답에 다음 헤더가 포함됩니다:
- `X-Process-Time`: 요청 처리 시간 (초)
- `X-Cache`: 캐시 상태 (HIT/MISS)

## 공통 응답 형식
모든 API는 다음과 같은 형식으로 응답합니다:
```json
{
  "success": true,
  "message": "응답 메시지",
  "timestamp": "2025-07-28T01:00:00.000000",
  "data": {}
}
```

---

## ⚡ 1. 기본 시스템 API

### 시스템 상태 확인 (강화됨!)
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
    "database": "connected",
    "services": "initialized"  // 새로 추가!
  }
}
    "database": "connected"
  }
}
```

### API 루트 정보 (업데이트됨!)
```javascript
fetch('http://localhost:8000/')
  .then(response => response.json())
  .then(data => console.log(data));

// 응답 예시:
{
  "success": true,
  "message": "Trading CORE API가 정상적으로 작동 중입니다.",
  "data": {
    "name": "Trading CORE API",
    "version": "1.0.0",
    "status": "healthy"  // 애플리케이션 상태 표시
  }
}
```

---

## ⚡ 2. 데이터 조회 API (`/api/v1/data`) - 캐싱 최적화!

### 실시간 K-라인 데이터 (성능 개선!)
> **💡 캐시 정보**: 5초 TTL - 동일 요청 시 즉시 응답!

```javascript
// 실시간 최신 1개 데이터 (Redis에서 실시간 데이터)
fetch('http://localhost:8000/api/v1/data/realtime/klines?symbol=BTCUSDT&interval=1m&limit=1')
  .then(response => {
    console.log('캐시 상태:', response.headers.get('X-Cache')); // HIT/MISS
    console.log('처리 시간:', response.headers.get('X-Process-Time')); // 처리 시간
    return response.json();
  })
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

### 실시간 거래 데이터 (캐싱 적용!)
> **💡 캐시 정보**: 10초 TTL

```javascript
// 최근 거래 내역
fetch('http://localhost:8000/api/v1/data/realtime/trades?symbol=BTCUSDT&limit=50')
  .then(response => {
    console.log('캐시:', response.headers.get('X-Cache'));
    return response.json();
  })
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

## ⚡ 4. 주문/포지션 관리 API (`/api/v1/orders`) - 캐싱 적용!

### 현재 포지션 조회 (성능 향상!)
> **💡 캐시 정보**: 30초 TTL - 포지션 정보 빠른 조회!

```javascript
fetch('http://localhost:8000/api/v1/orders/positions')
  .then(response => {
    console.log('캐시 상태:', response.headers.get('X-Cache'));
    console.log('처리 시간:', response.headers.get('X-Process-Time'));
    return response.json();
  })
  .then(data => {
    const positions = data.data.data.positions;
    positions.forEach(pos => {
      console.log(`심볼: ${pos.symbol}, 사이즈: ${pos.size}, PnL: ${pos.unrealized_pnl}`);
    });
  });
```

### 계정 정보 조회 (최적화!)
> **💡 캐시 정보**: 60초 TTL - 계정 정보 효율적 조회!
```javascript
// 선물 계정
fetch('http://localhost:8000/api/v1/orders/account/futures')
  .then(response => {
    console.log('캐시 상태:', response.headers.get('X-Cache'));
    return response.json();
  })
  .then(data => console.log(data));

// 현물 계정
fetch('http://localhost:8000/api/v1/orders/account/spot')
  .then(response => response.json())
  .then(data => console.log(data));
```

### 오픈 주문 조회
```javascript
// 모든 오픈 주문
fetch('http://localhost:8000/api/v1/orders/open')
  .then(response => response.json())
  .then(data => console.log(data));

// 특정 심볼의 오픈 주문
fetch('http://localhost:8000/api/v1/orders/open?symbol=BTCUSDT')
  .then(response => response.json())
  .then(data => console.log(data));
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
.then(response => response.json())
.then(data => console.log(data));
```

### 신호 처리 (POST) - 에러 핸들링 강화!
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

## 5. 거래 설정 API (`/api/v1/settings`) - 완전한 CRUD 지원! 🆕

### 현재 설정 조회 (GET)
```javascript
fetch('http://localhost:8000/api/v1/settings/trading')
  .then(response => response.json())
  .then(data => {
    const settings = data.data;
    console.log(`레버리지: ${settings.LEVERAGE}x`);
    console.log(`리스크: ${settings.RISK_PER_TRADE * 100}%`);
    console.log(`자동거래: ${settings.AUTO_TRADING_ENABLED}`);
  });

// 응답 예시:
{
  "success": true,
  "message": "거래 설정을 성공적으로 조회했습니다.",
  "data": {
    "LEVERAGE": 10,
    "RISK_PER_TRADE": 0.02,
    "AUTO_TRADING_ENABLED": false,
    "TIMEFRAME": "1m",
    "ACCOUNT_BALANCE": 10000.0,
    // ... 다른 설정들
  }
}
```

### 전체 설정 업데이트 (POST)
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
.then(data => {
  console.log('설정 업데이트 완료:', data.data);
});
```

### 🆕 개별 설정 업데이트 (PATCH)
```javascript
// 레버리지만 변경
fetch('http://localhost:8000/api/v1/settings/trading/LEVERAGE', {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    "value": 25
  })
})
.then(response => response.json())
.then(data => {
  console.log('이전 값:', data.data.old_value);
  console.log('새 값:', data.data.new_value);
  console.log('전체 설정:', data.data.updated_settings);
});

// 자동거래 토글
fetch('http://localhost:8000/api/v1/settings/trading/AUTO_TRADING_ENABLED', {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    "value": true
  })
})
.then(response => response.json())
.then(data => console.log('자동거래 활성화:', data));

// 리스크 비율 조정
fetch('http://localhost:8000/api/v1/settings/trading/RISK_PER_TRADE', {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    "value": 0.015
  })
})
.then(response => response.json())
.then(data => console.log('리스크 조정:', data));

// 활성 시간 설정
fetch('http://localhost:8000/api/v1/settings/trading/ACTIVE_HOURS', {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    "value": [[8, 23], [0, 3]]
  })
})
.then(response => response.json())
.then(data => console.log('활성 시간 변경:', data));
```

### 🆕 설정 초기화 (POST)
```javascript
// 모든 설정을 기본값으로 초기화
fetch('http://localhost:8000/api/v1/settings/trading/reset', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('이전 설정:', data.data.previous_settings);
  console.log('새 설정:', data.data.new_settings);
  console.log('초기화 완료 시간:', data.data.reset_timestamp);
});

// 응답 예시:
{
  "success": true,
  "message": "거래 설정이 기본값으로 성공적으로 초기화되었습니다.",
  "data": {
    "previous_settings": {
      "LEVERAGE": 25,
      "AUTO_TRADING_ENABLED": true,
      // ... 이전 설정들
    },
    "new_settings": {
      "LEVERAGE": 10,
      "AUTO_TRADING_ENABLED": false,
      // ... 기본 설정들
    },
    "reset_timestamp": "2025-07-28T02:30:00.000000"
  }
}
```

### 🔧 실용적인 사용 예시

#### React Hook으로 설정 관리
```jsx
import { useState, useEffect } from 'react';

function useTraidngSettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);

  // 설정 로드
  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/settings/trading');
      const data = await response.json();
      if (data.success) {
        setSettings(data.data);
      }
    } catch (error) {
      console.error('설정 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 개별 설정 업데이트
  const updateSetting = async (key, value) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/settings/trading/${key}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value })
      });
      const data = await response.json();
      if (data.success) {
        setSettings(data.data.updated_settings);
        return true;
      }
    } catch (error) {
      console.error('설정 업데이트 실패:', error);
      return false;
    }
  };

  // 설정 초기화
  const resetSettings = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/settings/trading/reset', {
        method: 'POST'
      });
      const data = await response.json();
      if (data.success) {
        setSettings(data.data.new_settings);
        return true;
      }
    } catch (error) {
      console.error('설정 초기화 실패:', error);
      return false;
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  return {
    settings,
    loading,
    updateSetting,
    resetSettings,
    reload: loadSettings
  };
}

// 컴포넌트에서 사용
function SettingsPanel() {
  const { settings, updateSetting, resetSettings } = useTraidngSettings();

  const handleLeverageChange = (newLeverage) => {
    updateSetting('LEVERAGE', parseInt(newLeverage));
  };

  const toggleAutoTrading = () => {
    updateSetting('AUTO_TRADING_ENABLED', !settings.AUTO_TRADING_ENABLED);
  };

  return (
    <div>
      <h2>거래 설정</h2>
      
      <div>
        <label>레버리지: </label>
        <input 
          type="number" 
          value={settings?.LEVERAGE || 10}
          onChange={(e) => handleLeverageChange(e.target.value)}
        />
      </div>
      
      <div>
        <label>
          <input 
            type="checkbox" 
            checked={settings?.AUTO_TRADING_ENABLED || false}
            onChange={toggleAutoTrading}
          />
          자동거래 활성화
        </label>
      </div>
      
      <button onClick={resetSettings}>
        기본값으로 초기화
      </button>
    </div>
  );
}
```

#### 설정 검증 유틸리티
```javascript
// 설정 유효성 검사 함수
function validateSettingValue(key, value) {
  const validations = {
    LEVERAGE: (v) => v >= 1 && v <= 125,
    RISK_PER_TRADE: (v) => v > 0 && v <= 1,
    ACCOUNT_BALANCE: (v) => v > 0,
    ATR_MULTIPLIER: (v) => v > 0,
    TP_RATIO: (v) => v > 0,
    MIN_SIGNAL_INTERVAL_MINUTES: (v) => v >= 1,
    MAX_CONSECUTIVE_LOSSES: (v) => v >= 1,
  };

  if (validations[key]) {
    return validations[key](value);
  }
  return true;
}

// 안전한 설정 업데이트
async function safeUpdateSetting(key, value) {
  if (!validateSettingValue(key, value)) {
    throw new Error(`Invalid value for ${key}: ${value}`);
  }

  const response = await fetch(`http://localhost:8000/api/v1/settings/trading/${key}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value })
  });

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.message);
  }

  return data.data;
}
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

### JavaScript 에러 처리 예시 (강화된 버전!)
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
    
    // 성능 정보 출력
    console.log(`⚡ 처리 시간: ${response.headers.get('X-Process-Time')}초`);
    console.log(`💾 캐시 상태: ${response.headers.get('X-Cache') || 'NONE'}`);
    
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

---

## � 최신 개선사항 (2025년 7월 28일) - FastAPI 리팩토링 완료!

### 📈 성능 최적화
1. **응답 캐싱 시스템**: Redis 기반 지능형 캐싱
   - K-라인 데이터: 5초 TTL (빠른 차트 업데이트)
   - 거래 데이터: 10초 TTL (실시간성 유지)
   - 포지션 정보: 30초 TTL (안정적 조회)
   - 계정 정보: 60초 TTL (효율적 관리)

2. **성능 모니터링**: 모든 응답에 성능 헤더 제공
   - `X-Process-Time`: 실제 처리 시간 측정
   - `X-Cache`: 캐시 히트/미스 상태 표시

### 🛡️ 안정성 강화
1. **에러 핸들링 미들웨어**: 전역 예외 처리
   - 비즈니스 로직 예외 (400)
   - 유효성 검사 오류 (422) 
   - 서버 내부 오류 (500)

2. **포지션 모니터링**: 백그라운드 에러 핸들링 강화
   - 상세한 스택 트레이스 로깅
   - 안전한 데이터 로딩 메커니즘

### ⚙️ 아키텍처 개선
1. **애플리케이션 팩토리 패턴**: 깔끔한 코드 구조
2. **계층화된 미들웨어**: CORS → 에러 → 로깅 → 캐시 순서
3. **개선된 의존성 주입**: 효율적인 서비스 관리
4. **설정 관리 개선**: 환경별 설정 분리

### 🔧 개발자 경험 개선
1. **자동 CORS 설정**: 프론트엔드 개발 편의성
2. **상세한 로깅**: 요청/응답 자동 추적
3. **헬스체크 강화**: 서비스 상태 실시간 모니터링

이 가이드를 참고하여 프론트엔드에서 Trading CORE API를 효율적으로 활용하실 수 있습니다.

**프론트엔드에서 빠른 요청이 가능한 이유**: Redis 캐시 + 최적화된 미들웨어 파이프라인 덕분입니다! 🚀  
   - 포지션 정보: 15초 캐싱
   - 계정 정보: 30초 캐싱

2. **로깅 최적화**: 불필요한 INFO 로그를 DEBUG로 변경하여 로그 스팸 감소

3. **Binance API 보호**: IP 차단 시 캐시 데이터로 Fallback 처리

4. **성능 향상**: 동일한 요청에 대해 캐시된 응답으로 즉시 처리

💡 **캐싱 확인**: 응답 헤더의 `x-cache: HIT/MISS`로 캐시 상태 확인 가능
