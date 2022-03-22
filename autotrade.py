import datetime
from datetime import timedelta
import time
import pyupbit
import jwt   # PyJWT 
import uuid
import requests
import hashlib
from urllib.parse import urlencode

# aws 서버에서 돌릴때는 decode('utf-8')을 지워준다.

access_key ='access_key'
secret_key ='secret_key'
upbit = pyupbit.Upbit(access_key, secret_key)

#------------------------------------------------------------
# slack-bot
mytoken = 'stack_mytoken'
channel = '#stock'              # 채널설정


def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
    print(response)
# slack-bot
#------------------------------------------------------------

data_count = 15
coin = "BTC"            # coin kind
coin_KRW = "KRW-" + coin # 50번재 줄

interval = 'minute1'             # 26줄째 줄, 이동평균선 240분(4시간), 60분(1시간), 30분 정하기
MA_NUMBER = 5                     # 단순 MA5 = 5, 단순 MA10 = 10, 단순 MA60 =60

# 몇분동안 실행시킬것인가. running time
end_time = datetime.datetime.now() +timedelta(days=30) # 60분만 돌아가게 만들자.


def get_ma(ticker): # ticker 예시 "KRW-BTC"
    """이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval= interval,
    count=data_count)  # 4시간
    ma10 = df['close'].rolling(MA_NUMBER).mean()
    return ma10


print("---------------------------------------------------------------------------------------------------------")
print("autotrade start : ", datetime.datetime.now()) # 자동매매 시작
# slack-bot------------------------------
slack_text = "autotrade start : "+ str(datetime.datetime.now())
post_message(mytoken, channel, slack_text)
# slack-bot------------------------------


def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]


# end_time = datetime.datetime.now() +timedelta(minutes=3) # 1분만 돌아가게 만들자.
# 1분만 돌아가게 만들어보자.

BTC_balance =0
BTC_TO_KRW_BALANCE = 0
BTC_buy_price = 0

while (datetime.datetime.now() < end_time ):
    try:
        ma10 = get_ma(coin_KRW) # 10 이동평균선        
        current_ma10 = ma10[len(ma10)-1] # 10 이동평균선 현재값
        current_ma10_2 = ma10[len(ma10)-2] # 10 이동평균선 끝에서 2번째 값
        current_ma10_3 = ma10[len(ma10)-3] # 10 이동평균선 끝에서 3번째 값

        first = current_ma10_2-current_ma10_3
        second = current_ma10-current_ma10_2
        # 매수조건
        # -----------------------------------------------------------------------------
        if (first < 0) and (first *second <0) :
            #----------------------------------------------------------------
            # 잔고 조회 start
            """잔고 조회"""
            payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            }

            # decode 해주면 된다.
            jwt_token = jwt.encode(payload, secret_key).decode('utf8')
            authorization_token = 'Bearer {}'.format(jwt_token)


            headers = {"Authorization": authorization_token}
            res = requests.get('https://api.upbit.com/v1/accounts', headers=headers)
            data = res.json()

            KRW_balance = float(data[0]['balance'])*0.995 # 내 원화 자산, int, 수수료 생각해서, 0.5% 빼고

            # print(KRW_balance) # 현재 내 원화 자산
            """잔고 조회 끝"""
            # 잔고 조회 end
            #----------------------------------------------------------------     

            if KRW_balance > 5000: # 여기 KRW_balance는 int
                print('---------------------------------buy-------------------------------------------')
                
                # slack-bot------------------------------
                slack_text = '---------------------------------buy-------------------------------------------'
                post_message(mytoken, channel, slack_text)
                # slack-bot------------------------------

                #----------------------------------------------------------------
                # 매수 시작 start
                KRW_balance = str(KRW_balance) # str로 바꿔준다.
                """매수 시작"""
                query = {
                    'market': coin_KRW,
                    'side': 'bid',
                    'price': KRW_balance,
                    'ord_type': 'price',
                    "identifier": str(uuid.uuid4())# 거래할때 마다 바꾸어줘야함.

                }
                query_string = urlencode(query).encode()

                m = hashlib.sha512()
                m.update(query_string)
                query_hash = m.hexdigest()

                payload = {
                    'access_key': access_key,
                    'nonce': str(uuid.uuid4()), # str(uuid.uuid4()) : 랜덤 문자열 생성
                    'query_hash': query_hash,
                    'query_hash_alg': 'SHA512',
                }

                current_price = get_current_price(coin_KRW) # BTC 현재가격

                jwt_token = jwt.encode(payload, secret_key).decode('utf8')
                authorize_token = 'Bearer {}'.format(jwt_token)
                headers = {"Authorization": authorize_token}
                res = requests.post("https://api.upbit.com/v1/orders", params=query, headers=headers)
                data = res.json()
                print(data)
                print("거래시간 : ", data['created_at']) # 거래시간
                print("주문번호 : " ,data['uuid']) # 주문번호
                print("코인종류 : ", data['market']) # 코인종류
                print("거래종류 : ", data['side']) # 매수
                print("내가 쓴 돈(수수료포함) : ", data['locked']) # 내가 사용한 금액
                print("거래수수료 : ", data['remaining_fee'])  # 수수료
                print("매수 금액 : " ,data['price']) # 내가 산 금액
                print("비트코인 매수가 : ", current_price)
                print("비트코인 매수 개수 : ", round( float(data['price'])/current_price, 10)) # 소수점 10자리까지 나타냄
                """매수 끝"""
                # 매수 end
                #---------------------------------------------------------------

                coin_bid_price =current_price # coin_bid_price 매수한 금액
                # (coin_bid_price-current_price)/(coin_bid_price) > 0.02 # 잘못 결정해서 -2% 이상으로 손해보면 팔아버려라.

                # slack-bot------------------------------
                slack_text = "거래시간 : " + data['created_at'] + "\n" + "주문번호 : " +data['uuid'] + "\n" + "코인종류 : " + data['market'] + "\n" + "거래종류 : " + data['side']  + "\n" + "매수 금액 : " + data['price']  + "\n" + "비트코인 매수가 : "+ str(current_price)  + "\n" + "비트코인 매수 개수 : " + str( round( float(data['price'])/current_price, 10) )
                 
                post_message(mytoken, channel, slack_text)
                # slack-bot------------------------------
       
        

        # btc = get_balance("TC") # 현재 가지고 있는 btc의 잔고를 가져온다.
        ma10 = get_ma(coin_KRW) # 10 이동평균선
    
        current_ma10 = ma10[len(ma10)-1] # 10 이동평균선 현재값
        current_ma10_2 = ma10[len(ma10)-2] # 10 이동평균선 끝에서 2번째 값
        current_ma10_3 = ma10[len(ma10)-3] # 10 이동평균선 끝에서 3번째 값

        first = current_ma10_2-current_ma10_3
        second = current_ma10-current_ma10_2
        
        # 매도조건 (BTC)
        # -----------------------------------------------------------------------------
        if (first > 0) and (first * second < 0) :
           # 매도 (BTC)
            # -----------------------------------------------------------------------------   
            # 잔고 조회 start
            """잔고 조회"""
            payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            }

            # decode 해주면 된다.
            jwt_token = jwt.encode(payload, secret_key).decode('utf8')
            authorization_token = 'Bearer {}'.format(jwt_token)


            headers = {"Authorization": authorization_token}
            res = requests.get('https://api.upbit.com/v1/accounts', headers=headers)
            data = res.json()
            # print(data)

            BTC_buy_price = 0                       # 여기서 0을 만들어줘야, 밑에서 sell을 계속 안한다.

            for i in list(range(0,len(data))):
                if data[i]['currency'] == coin:                                        # BTC인거 찾아라
                    print('비트코인 보유량 : ', data[i]['balance'])                     # BTC 보유개수를 보여줘, 형식 str
                    print('비트코인 매수가 : ', data[i]['avg_buy_price'])               # BTC 매수가
                    BTC_balance = data[i]['balance']                
                    BTC_buy_price = data[i]['avg_buy_price']                           # 비트코인 매수가


            # print(float(BTC_balance)*0.995) # int로 바꿈
            # print(float(BTC_balance))
            BTC_balance = float(BTC_balance) # 비트코인 보유개수 int로 바꿈
            BTC_buy_price =float(BTC_buy_price ) # 비트코인 매수가 int로 바꿈


            BTC_TO_KRW_BALANCE = BTC_balance * BTC_buy_price # 비트코인 총 매수 금액
            # print(BTC_TO_KRW_BALANCE)
     
            if (BTC_TO_KRW_BALANCE > 5000) : # BTC_TO_KRW_BALANCE는 int
                #----------------------------------------------------------------
                # 매도 시작 start
                print('---------------------------------sell-------------------------------------------')
                # slack-bot------------------------------
                slack_text = '---------------------------------sell-------------------------------------------'
                post_message(mytoken, channel, slack_text)
                # slack-bot------------------------------


                BTC_balance = str(BTC_balance) # 비트코인 volume : str로 바꿈
                query = {
                    'market': coin_KRW,
                    'side': 'ask',
                    'volume': BTC_balance,
                    'ord_type': 'market',
                    "identifier":  str(uuid.uuid4())

                }
                query_string = urlencode(query).encode()

                m = hashlib.sha512()
                m.update(query_string)
                query_hash = m.hexdigest()

                payload = {
                    'access_key': access_key,
                    'nonce': str(uuid.uuid4()),
                    'query_hash': query_hash,
                    'query_hash_alg': 'SHA512',
                }

                jwt_token = jwt.encode(payload, secret_key).decode('utf8') # utf8을 꼭 붙여야한다.
                authorize_token = 'Bearer {}'.format(jwt_token)
                headers = {"Authorization": authorize_token}

                current_price = get_current_price(coin_KRW) # BTC 현재가격

                res = requests.post("https://api.upbit.com/v1/orders", params=query, headers=headers)
                data = res.json()
                print(data)
                print("매도 시간 : ", data['created_at']) # 거래시간
                print("주문 번호 : " ,data['uuid']) # 주문번호
                print("코인 종류 : ", data['market']) # 코인종류
                print("거래 종류 : ", data['side']) # 매도
                print("매도 수량 : ", data['locked']) # 내가 사용한 금액
                print("매도 금액(수수료포함) : ", current_price *float(data['locked']) )
                print("매도가 : ", current_price)
                print("수익률 : ", str(round((current_price - BTC_buy_price)/(BTC_buy_price),3)),"%" )# (매도가 - 매수가)/매수가, 수익률

                # slack-bot------------------------------
                slack_text = "매도 시간 : " + data['created_at'] + "\n" + "주문 번호 : " + data['uuid'] + "\n" + "코인 종류 : " + data['market'] + "\n"  + "거래 종류 : " + data['side']  + "\n" + "매도 수량 : " + data['locked']  + "\n" + "매도 금액(수수료포함) : " + str( current_price *float(data['locked']) )  + "\n" + "매도가 : " + str(current_price) + "\n" + "수익률 : " + str( round( (current_price - BTC_buy_price) / (BTC_buy_price) ,3) ) + "%"

                post_message(mytoken, channel, slack_text)
                # slack-bot------------------------------
            
                
        
        time.sleep(1)    
    except Exception as e:
        print(e)
        # post_message(myToken,"#crypto", e)
        time.sleep(1)


print("---------------------------------------------------------------------------------------------------------")

print("autotrade end : ", end_time)