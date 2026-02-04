import streamlit as st
import pandas as pd
import yfinance as yf
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta # 맨 윗부분에 추가

# 1. 페이지 설정
st.set_page_config(page_title="SIDO Global Radar", layout="wide")

# [함수] 시장 인덱스 판별 및 RSI 계산
def get_market_index(ticker):
    ticker = ticker.upper()
    if ticker.endswith('.KS') or ticker.endswith('.KQ'): return '^KS11', 'KOSPI'
    elif ticker.endswith('.T'): return '^N225', 'Nikkei225'
    elif ticker.endswith('.HK'): return '^HSI', 'Hang Seng'
    elif ticker.endswith('.SS') or ticker.endswith('.SZ'): return '^SSEC', 'Shanghai'
    elif ticker.endswith('.VN'): return '^VNINDEX.VN', 'VN Index'
    else: return '^GSPC', 'S&P500'

# 1. 배경색 설정 (눈이 편한 회색 톤)
# 다크모드가 너무 검어서 힘들 때는 #2D2D2D (진회색)가 가장 좋습니다.
bg_color = "#2D2D2D"


def calculate_rsi(data, window=14):
    delta = data.diff(); gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# -------------------------------------------
# 2. 사이드바 (종목명/티커 예제 풀버전 복구)
# -------------------------------------------
with st.sidebar:
    st.header("🚀 SIDO RADAR")
    st.markdown("---")
    st.subheader("🔎 TICKER EXAMPLES")
    st.write("• 🇰🇷 **KR** : 삼성바이오로직스 (207940.KS)")
    st.write("• 🇺🇸 **US** : 버티브 (VRT)")
    st.write("• 🇯🇵 **JP** : 히타치 (6501.T)")
    st.write("• 🇨🇳 **CN** : BYD (002594.SZ) / 귀주모태주 (600519.SS)")
    st.write("• 🇭🇰 **HK** : 텐센트 (0700.HK)")
    st.write("• 🇻🇳 **VN** : 빈그룹 (VIC.VN)")
    st.markdown("---")
    st.subheader("📊 BENCHMARK")
    st.text("KOSPI: ^KS11\nS&P500: ^GSPC\nNIKKEI: ^N225")

# -------------------------------------------
# 3. 메인 메뉴 구성
# -------------------------------------------
st.title("🌐 GLOBAL INVESTMENT RADAR")
menu = st.radio("MENU SELECT", ["🔍 개별 종목 즉석 퀀트", "⚖️ 다중 종목 비교 분석"], horizontal=True)



# --- [메뉴 1: 개별 종목 즉석 퀀트 (현재가 기반)] ---
if menu == "🔍 개별 종목 즉석 퀀트":
    st.subheader("현재가 기반 실시간 퀀트 분석")
    c1, c2 = st.columns([2, 1])
    with c1: target_ticker = st.text_input("분석 티커 입력", placeholder="예: 207940.KS").upper()
    with c2: manual_p = st.number_input("기준가 직접 입력(선택)", value=0.0)

    if st.button("📊 즉석 분석 실행"):
        if target_ticker:
            with st.spinner('데이터 분석 중...'):
                stock = yf.Ticker(target_ticker); hist = stock.history(period='1y')
                idx_symbol, idx_name = get_market_index(target_ticker)
                idx_data = yf.download(idx_symbol, period='1y', progress=False)

                # --- [추가/수정] Multi-Index 컬럼 문제 해결 ---
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
                if isinstance(idx_data.columns, pd.MultiIndex): idx_data.columns = idx_data.columns.get_level_values(0)


                if not hist.empty:
                    curr_p = manual_p if manual_p > 0 else hist['Close'].iloc[-1]
                    derived_target = curr_p * 1.10 # 역산 적정주가 가이드
                    
                    # 200일선 예외처리 및 RSI
                    ma200 = hist['Close'].rolling(window=200).mean() if len(hist) >= 200 else hist['Close'].expanding().mean()
                    rsi_series = calculate_rsi(hist['Close']); curr_rsi = rsi_series.iloc[-1]

                    # 3. 플롯 범위 제한 (최근 6개월)
                    six_months_ago = (hist.index[-1] - pd.Timedelta(days=180)).replace(tzinfo=None)
                    hist.index = hist.index.tz_localize(None) # 이 줄을 추가하면 확실합니다.
                    hist_plot = hist.loc[six_months_ago:]
                    ma_plot = ma200.loc[six_months_ago:]
                    rsi_plot = rsi_series.loc[six_months_ago:]
                    idx_plot = idx_data.loc[six_months_ago:] if not idx_data.empty else pd.DataFrame()

                    # 시그널 화살표
                    if curr_rsi < 35: sig = "▲ BUY (Low RSI)"; col = "green"
                    elif curr_rsi > 65: sig = "▼ SELL (High RSI)"; col = "red"
                    else: sig = "● HOLD (Neutral)"; col = "gray"

                    st.markdown(f"### {sig} | {target_ticker}")

                    # 시그널 결정 로직 바로 아래 추가
                    # --- [추가] 분석 요약 수치 출력 ---
                    col_info1, col_info2, col_info3 = st.columns(3)
                    col_info1.metric("현재가", f"{curr_p:,.2f}")
                    col_info2.metric("목표가(가이드)", f"{derived_target:,.2f}")
                    col_info3.metric("현재 RSI", f"{curr_rsi:.2f}")


                    # 차트 및 대시보드 출력 (생략된 기존 Plotly 로직 그대로)
                    # 4. 차트 생성
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

                    # (1) 현재가 선 - 형광 연두색
                    fig.add_trace(go.Scatter(x=hist_plot.index, y=hist_plot['Close'], name='Price (현재가)', 
                                           line=dict(color='#7FFF00', width=3)), row=1, col=1)

                    # (2) 200일선 - 주황색 점선
                    fig.add_trace(go.Scatter(x=ma_plot.index, y=ma_plot, name='200MA (생명선)', 
                                           line=dict(color='orange', width=2, dash='dot')), row=1, col=1)

                    # (3) 인덱스 지수 - 금색(#FFD700)으로 변경 (가시성 확보)
                    #if not idx_plot.empty:
                        # 6개월 시작점 기준으로 수익률 동기화
                    #    idx_scaled = (idx_plot['Close'] / idx_plot['Close'].iloc[0]) * hist_plot['Close'].iloc[0]
                    #    fig.add_trace(go.Scatter(x=idx_plot.index, y=idx_scaled, name=f'Index({idx_name})', 
                    #                           line=dict(color="#F7D514", width=2, dash='dash')), row=1, col=1)
                    # --- [인덱스 지수 출력부 수정] ---
                    # --- [인덱스 지수 출력부 확실한 수정] ---
                    #if not idx_data.empty:
                    #    idx_p = idx_data['Close'].loc[six_months_ago:] # ['Close']를 명시해줘야 안전합니다.
                    #    h_p = hist['Close'].loc[six_months_ago:]
    
                        # 수익률 동기화: 6개월 전 첫 값을 기준으로 현재 주가 스케일에 맞춤
                    #    idx_scaled = (idx_p / idx_p.iloc[0]) * h_p.iloc[0]
    
                    #    fig.add_trace(go.Scatter(
                    #        x=idx_p.index, 
                    #        y=idx_scaled, 
                    #        name=f'Index({idx_name})', 
                    #       line=dict(color='#FFFF00', width=2, dash='dash') # 밝은 노랑
                    #    ), row=1, col=1)
                    # --- [수정] 인덱스 지수 출력부 ---
                    if not idx_data.empty:
                        idx_p = idx_data['Close'].loc[six_months_ago:].squeeze() 
                        h_p = hist['Close'].loc[six_months_ago:].squeeze()
   
                        idx_scaled = (idx_p / idx_p.iloc[0]) * h_p.iloc[0]
   
                        fig.add_trace(go.Scatter(
                            x=idx_p.index,
                            y=idx_scaled,
                            name=f'Index({idx_name})',
                           line=dict(color='#FFFF00', width=2, dash='dash')
                        ), row=1, col=1)
                    
                    

                    # (4) RSI 미니차트 (화살표 제거)
                    #fig.add_trace(go.Scatter(x=rsi_plot.index, y=rsi_plot, name='RSI', 
                    #                       line=dict(color='cyan', width=2)), row=2, col=1)
                    # (3) RSI 및 화살표 시그널
                    #fig.add_trace(go.Scatter(x=r_p.index, y=r_p, name='RSI', line=dict(color='cyan', width=2)), row=2, col=1)
                    
                    # RSI 매수/매도 화살표 추가 (30이하 BUY ▲, 70이상 SELL ▼)
                    # --- [변수명 정리 및 RSI 화살표 로직 수정] ---
                    
                    # r_p 대신 rsi_plot으로 통일하는 것이 안전합니다.
                    rsi_plot = rsi_series.loc[six_months_ago:] 

                    fig.add_trace(go.Scatter(x=rsi_plot.index, y=rsi_plot, name='RSI', line=dict(color='cyan', width=2)), row=2, col=1)

                    # RSI 매수/매도 화살표 (변수명을 rsi_plot으로 수정)
                    buy_signals = rsi_plot[rsi_plot <= 30]
                    sell_signals = rsi_plot[rsi_plot >= 70]

                    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals, mode='markers', name='BUY ▲',
                                           marker=dict(symbol='triangle-up', size=12, color='lime')), row=2, col=1)
                    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals, mode='markers', name='SELL ▼',
                                           marker=dict(symbol='triangle-down', size=12, color='red')), row=2, col=1)

                    #fig.update_layout(height=700, template="plotly_dark", paper_bgcolor="#2D2D2D", plot_bgcolor="#2D2D2D",
                                    #xaxis=dict(range=[six_months_ago, hist.index[-1]]), margin=dict(l=20, r=20, t=50, b=20))
                    #st.plotly_chart(fig, use_container_width=True)

                    # 5. 레이아웃 (눈이 편한 배경색 적용)
                    # --- [X축 범위 고정 (6개월만 보이게)] ---
                    # 5. 레이아웃 (범례 가시성 및 다크모드 최적화)
                    fig.update_layout(
                        height=700,
                        paper_bgcolor="#2D2D2D",
                        plot_bgcolor="#2D2D2D",
                        template="plotly_dark",
                        # 범례 폰트 색상을 명시적으로 흰색으로 고정하고 배경을 약간 투명하게 설정
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                            font=dict(size=12, color="white"), # 범례 폰트 색상 강제 지정
                            bgcolor="rgba(0,0,0,0)" # 배경 투명
                        ),
                        margin=dict(l=20, r=20, t=80, b=20), # 범례가 겹치지 않게 상단 여백 확보
                        xaxis=dict(
                            range=[six_months_ago, hist.index[-1]], 
                            gridcolor="#444444",
                            tickfont=dict(color="white") # 축 글자 색상
                        ),
                        yaxis=dict(gridcolor="#444444", tickfont=dict(color="white")),
                        xaxis2=dict(gridcolor="#444444", tickfont=dict(color="white")),
                        yaxis2=dict(gridcolor="#444444", tickfont=dict(color="white"))
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    

# --- [메뉴 2: 다중 종목 비교 분석 (복구 완료!)] ---
# --- [메뉴 2: 다중 종목 비교 분석 (복구 및 수정)] ---
elif menu == "⚖️ 다중 종목 비교 분석":
    st.subheader("여러 종목 및 인덱스 수익률 비교 (최근 6개월 집중)")
    tickers_input = st.text_input("비교할 티커들을 쉼표(,)로 입력", placeholder="VRT, NVDA, 207940.KS").upper()
    compare_idx = st.selectbox("기준 인덱스 선택", ["^GSPC", "^KS11", "^N225", "^HSI"])
    
    if st.button("⚖️ 상대 수익률 비교 시작"):
        if tickers_input:
            with st.spinner('최근 6개월 수익률 분석 중...'):
                ticker_list = [t.strip() for t in tickers_input.split(',')]
                start_6m = datetime.now() - pd.Timedelta(days=180) # datetime 에러 해결 지점
                comparison_df = pd.DataFrame()
                
                for t in ticker_list:
                    # --- [메뉴 2 데이터 로드 수정] ---
                    t_data = yf.download(t, start=start_6m, progress=False)
                    if not t_data.empty:
                        # 데이터가 MultiIndex인 경우를 대비해 ['Close']를 안전하게 추출
                        comparison_df[t] = (t_data['Close'] / t_data['Close'].iloc[0]) * 100
                
                idx_c = yf.download(compare_idx, start=start_6m, progress=False)['Close']
                if not idx_c.empty:
                    comparison_df[f'INDEX({compare_idx})'] = (idx_c / idx_c.iloc[0]) * 100
                
                if not comparison_df.empty:
                    fig_comp = go.Figure()
                    for col in comparison_df.columns:
                        is_idx = 'INDEX' in col
                        fig_comp.add_trace(go.Scatter(x=comparison_df.index, y=comparison_df[col], name=col,
                                                   line=dict(color='#FFFF00' if is_idx else None, 
                                                            width=3 if is_idx else 2, dash='dash' if is_idx else 'solid')))
                    fig_comp.update_layout(height=600, template="plotly_dark", paper_bgcolor="#2D2D2D", plot_bgcolor="#2D2D2D",  
                                           margin=dict(l=20, r=20, t=80, b=20), # 범례가 겹치지 않게 상단 여백 확보
                                           legend=dict(
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.02,
                                                xanchor="right",
                                                x=1,
                                                font=dict(size=12, color="white"), # 범례 폰트 색상 강제 지정
                                                bgcolor="rgba(0,0,0,0)" # 배경 투명
                                            )
                                            
                    )

                    st.plotly_chart(fig_comp, use_container_width=True)
