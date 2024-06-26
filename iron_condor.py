# Iron Condor Generator Program
import requests
from datetime import datetime, timedelta

# set up today
now = datetime.now()
date_today = str(now).split()[0]

# get this upcoming friday
days_until_friday = timedelta((4 - now.weekday()) % 7)
if str(days_until_friday)[0] == 0:
    duf = 7  # to make the code a bit simpler
    friday_date = now + timedelta(7)
else:
    duf = str(days_until_friday)[0]  # to make the code a bit simpler
    friday_date = now + days_until_friday
friday = str(friday_date).split()[0]


# asks the user for news
def get_news(TICKER):
    # for the news articles
    NEWS_API_KEY = "b0899bac3c284df1afb9e1128507c8e5"
    NEWS_ENDPOINT = "https://newsapi.org/v2/top-headlines"
    news_parameters = {
        "q": TICKER,
        "apiKey": NEWS_API_KEY,
    }

    # the following will give you the recent news on your selected ticker
    # helps form your opinion on how the market is doing
    news_response = requests.get(NEWS_ENDPOINT, params=news_parameters)
    news_response.raise_for_status()
    news_data = news_response.json()

    message = ""
    if news_data["totalResults"] == 0:
        message += f"There are no articles for {TICKER}."
    else:
        news_answer = input(f"Do you want news for {TICKER}? yes/no: ").lower()
        if news_answer == "yes":
            for _ in range(min(news_data["totalResults"], 3)):  # will print a maximum of 3 news articles
                message += f"{_ + 1}. {str(news_data['articles'][_]['description'])}" + "\n"
        print(message)  # prints the article(s)
   

class SetUp:
    def __init__(self):
        self.TICKER = input("What stock ticker would you like to use?: ").upper()  # can use this
        self.TICKER = "AAPL".upper()  # or this if you want to test the code

        # from TD Ameritrade
        self.CONSUMER_KEY = "YOUR OWN CONSUMER KEY"
        # the consumer key is not used for this API, but can be used for other Ameritrade APIs
        self.API_KEY = "YOUR OWN API KEY"
        self.endpoint = "https://api.tdameritrade.com/v1/marketdata/chains"  # the endpoint for this specific program
        self.my_url = f"{self.endpoint}?apikey={self.API_KEY}&symbol={self.TICKER}"
        self.TDA_LINK = \
            f"https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=http://localhost&client_id" \
            f"={self.API_KEY}%40AMER.OAUTHAP "

        self.stock_parameters = {
            "symbol": self.TICKER,
            "apikey": self.API_KEY,
            "strikeCount": 12,  # I found this value to work most of the time
            "fromDate": friday,
            "toDate": friday,  # can change this according to how far out you want the iron condor
        }

        # sets up the data set
        self.response = requests.get(self.endpoint, params=self.stock_parameters)
        self.response.raise_for_status()
        self.stock_data = self.response.json()
        self.start()

    # this starts the program
    def start(self):
        # print(self.response.text)  # to get the JSON able to be viewed in a JSON viewer
        get_news(self.TICKER)
        options = Options(self.stock_data, self.stock_parameters, self.TICKER)
        options.sentiment()


class Options:
    # initializes the Options Class with the standard values for the greeks
    def __init__(self, stock_data, stock_parameters, TICKER):
        # values recommended to be used if you are new to iron condors
        self.upper_put_delta = -0.3
        self.lower_put_delta = -0.2
        self.upper_call_delta = 0.3
        self.lower_call_delta = 0.2
        self.gamma_value = 0.1  # I tested this to be accurate
        self.vega_value = 0.2  # I tested this to be accurate
        self.stock_data = stock_data
        self.stock_parameters = stock_parameters
        self.TICKER = TICKER

    # this is what gives you the strike based on your sentiment, these are just my values
    def sentiment(self):  # upper means "upper range of risk", lower means the opposite
        mood = {  # gives a tuple depending on how the user is feeling
            "bullish": (-0.35, -0.20, 0.20, 0.10, 0.10, 0.20),  # hopeful of a stock rising in value
            "bearish": (-0.20, -0.10, 0.30, 0.20, 0.10, 0.20),  # hopeful of a stock decreasing in value
            "neutral": (-0.25, -0.15, 0.25, 0.15, 0.10, 0.20),  # slightly bullish for me
            "worried": (-0.15, -0.10, 0.15, 0.10, 0.08, 0.05),  # unlikely to be risky
        }
        sentiment_answer = input("How do you feel about the market? Bullish/Bearish/Neutral/Worried: ").lower()
        try:
            # tries to see if that input is in the hashmap
            if mood[sentiment_answer]:
                self.upper_put_delta = mood[sentiment_answer][0]
                self.lower_put_delta = mood[sentiment_answer][1]
                self.upper_call_delta = mood[sentiment_answer][2]
                self.lower_call_delta = mood[sentiment_answer][3]
                self.gamma_value = mood[sentiment_answer][4]
                self.vega_value = mood[sentiment_answer][5]
        except KeyError:
            # if there is a KeyError than the default values for the greeks are used
            pass
        try:
            # check if an options chain exists for the ticker this week
            tuple(self.stock_data[f"{'call'}ExpDateMap"][f"{friday}:{duf}"].items())[0][1][0]["delta"]
        except KeyError:
            # will occur if there was a KeyError, which happens when there are no options for this ticker for this week
            self.end(None, None, exist=False)
        else:
            # if an options chain exists for the ticker then the program will continue
            self.greeks(self.upper_put_delta, self.lower_put_delta, self.upper_call_delta, self.lower_call_delta,
                        self.gamma_value, self.vega_value)

    # gets the greeks for the iron condor options
    def greeks(self, upper_put_delta, lower_put_delta, upper_call_delta, lower_call_delta, gamma_value, vega_value):
        put_strike = None
        call_strike = None
        for _ in range(0, self.stock_parameters["strikeCount"]):
            option_types = ["call", "put"]
            for option_type in option_types:  # don't use theta for the weekly income model, but it can be incorporated
                delta = tuple(self.stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["delta"]
                if type(delta) == str:  # sometimes when Friday is too close, delta is NaN
                    delta = float(0)
                gamma = tuple(self.stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["gamma"]
                # theta = tuple(self.stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["theta"]
                vega = tuple(self.stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["vega"]
                if option_type == "put":
                    if self.get_short_put(upper_put_delta, lower_put_delta, delta, _) != 0 and \
                            gamma < gamma_value and vega < vega_value:
                        put_strike = self.get_short_put(upper_put_delta, lower_put_delta, delta, _)
                    else:
                        pass
                elif option_type == "call":  # can also be an "else" statement
                    if self.get_short_call(upper_call_delta, lower_call_delta, delta, _) != 0 and \
                            gamma < gamma_value and vega < vega_value:
                        call_strike = self.get_short_call(upper_call_delta, lower_call_delta, delta, _)
                    else:
                        pass
        self.end(put_strike, call_strike, exist=True)

    # gets the short put strike price
    def get_short_put(self, upper_put_delta, lower_put_delta, delta, _):
        if upper_put_delta < delta < lower_put_delta:
            strike = tuple(self.stock_data["putExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["strikePrice"]
        else:
            strike = 0
        return strike

    # gets the short call strike price
    def get_short_call(self, upper_call_delta, lower_call_delta, delta, _):
        if upper_call_delta > delta > lower_call_delta:
            strike = tuple(self.stock_data["callExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["strikePrice"]
        else:
            strike = 0
        return strike

    def end(self, put_strike, call_strike, exist):
        if put_strike and call_strike and exist:
            print(f"\nThe strike price for the {self.TICKER} short put is: {put_strike}.")
            print(f"The strike price for the {self.TICKER} short call is: {call_strike}.")
        else:
            if exist:
                print(f"\nIt is not recommended to execute an iron condor for {self.TICKER} expiring on {friday}.")
            else:
                print(f"\n{self.TICKER} does not have options for {friday}.")
        answer = input("Do you want to test another ticker? Yes/No: ").lower()
        if answer == "yes":
            SetUp()
        else:
            print("Have a productive day!")


# starts the main portion of the program
SetUp()

# Options Greeks:
# the rate of change between
# Delta: ... the option's price and a $1 change in the underlying stock price
# Theta: ... the option price and time
# Gamma: ... an option's delta and the underlying asset's price
# Vega: ... an option's value and the underlying asset's implied volatility
# Rho: ... an option's value and a 1% change in the interest rate
