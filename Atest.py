import cProfile
# set global variable flag
import Alpha
from Alpha import *
import Plot
from scipy.stats.mstats import gmean
import sys
import os
import matplotlib
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema

from Alpha import trendslope_apply, zlema, supersmoother_3p, highpass, cg_Oscillator

sys.setrecursionlimit(1000000)

array = [2, 5, 10, 20, 40, 60, 120, 240]


"""
Atest (Assettest): 
= Test strategy on individual asset and then mean them 
= COMPARE past time to now (relative to past)(quantile to past)
= NOT COMPARE what other stocks do (NOT relative to time/market)(quantile to others)

Btest (Backtest):
= COMPARE past time to now (relative to past)(quantile to past)
= COMPARE assets with other (relative to other)(quantile to others)
"""


def trend(df: pd.DataFrame, abase: str, thresh_log=-0.043, thresh_rest=0.7237, market_suffix: str = ""):
    a_all = [1] + array
    a_small = [str(x) for x in a_all][:-1]
    a_big = [str(x) for x in a_all][1:]

    rsi_name = indi_name(abase=abase, deri=f"{market_suffix}rsi")
    phase_name = indi_name(abase=abase, deri=f"{market_suffix}phase")
    rsi_abv = indi_name(abase=abase, deri=f"{market_suffix}rsi_abv")
    turnpoint_name = indi_name(abase=abase, deri=f"{market_suffix}turnpoint")
    under_name = indi_name(abase=abase, deri=f"{market_suffix}under")
    trend_name = indi_name(abase=abase, deri=f"{market_suffix}{ADeri.trend.value}")

    func = talib.RSI
    # RSI and CMO are the best. CMO is a modified RSI
    # RSI,CMO,MOM,ROC,ROCR100,TRIX

    # df[f"detrend{abase}"] = signal.detrend(data=df[abase])
    for i in a_all:  # RSI 1
        try:
            if i == 1:
                df[f"{rsi_name}{i}"] = (df[abase].pct_change() > 0).astype(int)
                print(df[f"{rsi_name}{i}"].dtype)
                # df[ rsi_name + "1"] = 0
                # df.loc[(df["pct_chg"] > 0.0), rsi_name + "1"] = 1.0
            else:
                df[f"{rsi_name}{i}"] = func(df[abase], timeperiod=i) / 100
                # df[f"{rsi_name}{i}"] = func(df[f"{rsi_name}{i}"], timeperiod=i) / 100

                # normalization causes error
                # df[f"{rsi_name}{i}"] = (df[f"{rsi_name}{i}"]-df[f"{rsi_name}{i}"].min())/ (df[f"{rsi_name}{i}"].max()-df[f"{rsi_name}{i}"].min())
        except Exception as e:  # if error happens here, then no need to continue
            print("error", e)
            df[trend_name] = np.nan
            return trend_name

    # Create Phase
    for i in [str(x) for x in a_all]:
        maximum = (thresh_log * math.log((int(i))) + thresh_rest)
        minimum = 1 - maximum

        high_low, high_high = list(df[f"{rsi_name}{i}"].quantile([0.70, 1]))
        low_low, low_high = list(df[f"{rsi_name}{i}"].quantile([0, 0.30]))

        # df[f"{phase_name}{i}"] = [1 if high_high > x > high_low else 0 if low_low < x < low_high else np.nan for x in df[f"{rsi_name}{i}"]]

    # rsi high abve low
    for freq_small, freq_big in zip(a_small, a_big):
        df[f"{rsi_abv}{freq_small}"] = (df[f"{rsi_name}{freq_small}"] > df[f"{rsi_name}{freq_big}"]).astype(int)

    # one loop to create trend from phase
    for freq_small, freq_big in zip(a_small, a_big):
        trendfreq_name = f"{trend_name}{freq_big}"  # freg_small is 2, freq_big is 240
        # the following reason is that none of any single indicator can capture all. one need a second dimension to create a better fuzzy logic

        # 2. find all points where freq_small is higher/over/abv freq_big
        df[f"{trendfreq_name}"] = np.nan
        df[f"{turnpoint_name}{freq_small}helper"] = df[f"{rsi_name}{freq_small}"] / df[f"{rsi_name}{freq_big}"]

        freq_small_top_low, freq_small_top_high = list(df[f"{rsi_name}{freq_small}"].quantile([0.97, 1]))
        freq_small_bot_low, freq_small_bot_high = list(df[f"{rsi_name}{freq_small}"].quantile([0, 0.03]))

        freq_big_top_low, freq_big_top_high = list(df[f"{rsi_name}{freq_big}"].quantile([0.96, 1]))
        freq_big_bot_low, freq_big_bot_high = list(df[f"{rsi_name}{freq_big}"].quantile([0, 0.04]))

        # if bottom big and small freq are at their alltime rare high
        # df.loc[(df[f"{rsi_name}{freq_big}"] > freq_big_top_low), f"{trendfreq_name}"] = 0
        # df.loc[(df[f"{rsi_name}{freq_big}"] < freq_big_bot_high), f"{trendfreq_name}"] = 1

        # df.loc[(df[f"{rsi_name}{freq_small}"] > freq_small_top_low), f"{trendfreq_name}"] = 0
        # df.loc[(df[f"{rsi_name}{freq_small}"] < freq_small_bot_high), f"{trendfreq_name}"] = 1

        # small over big
        df.loc[(df[f"{rsi_name}{freq_small}"] / df[f"{rsi_name}{freq_big}"]) > 1.01, f"{trendfreq_name}"] = 1
        df.loc[(df[f"{rsi_name}{freq_small}"] / df[f"{rsi_name}{freq_big}"]) < 0.99, f"{trendfreq_name}"] = 0

        # 2. find all points that have too big distant between rsi_freq_small and rsi_freq_big. They are the turning points
        # top_low, top_high = list(df[f"{turnpoint_name}{freq_small}helper"].quantile([0.98, 1]))
        # bot_low, bot_high = list(df[f"{turnpoint_name}{freq_small}helper"].quantile([0, 0.02]))
        # df.loc[ (df[f"{turnpoint_name}{freq_small}helper"]) < bot_high, f"{trendfreq_name}"] = 1
        # df.loc[ (df[f"{turnpoint_name}{freq_small}helper"]) > top_low, f"{trendfreq_name}"] = 0

        # 3. Create trend based on these two combined
        df[trendfreq_name] = df[trendfreq_name].fillna(method='ffill')
        # df.loc[(df[phase_name + freq_big] == 1) & (df[phase_name + freq_small] == 1), trendfreq_name] = 0
        # df.loc[(df[phase_name + freq_big] == 0) & (df[phase_name + freq_small] == 0), trendfreq_name] = 1

        # fill na based on the trigger points. bfill makes no sense here
        # df[trendfreq_name].fillna(method='ffill', inplace=True)
        # TODO MAYBE TREND can be used to score past day gains. Which then can be used to judge other indicators

    # remove RSI and phase Columns to make it cleaner
    a_remove = []
    for i in a_all:
        # a_remove.append(market_suffix + "rsi" + str(i))
        # a_remove.append(market_suffix + "phase" + str(i))
        pass
    LB.columns_remove(df, a_remove)

    # calculate final trend =weighted trend of previous TODO this need to be adjusted manually. But the weight has relative small impact
    return trend_name


def slopecross(df, abase, sfreq, bfreq, smfreq):
    """using 1 polynomial slope as trend cross over. It is much more stable and smoother than using ma
        slope is slower, less whipsaw than MACD, but since MACD is quicker, we can accept the whipsaw. In general usage better then slopecross
    """
    name = f"{abase, sfreq, bfreq, smfreq}"
    df[f"slope1_{name}"] = df[abase].rolling(sfreq).apply(trendslope_apply, raw=False)
    df[f"slope2_{name}"] = df[abase].rolling(bfreq).apply(trendslope_apply, raw=False)

    # df[f"slopediff_{name}"] = df[f"slope1_{name}"] - df[f"slope2_{name}"]
    # df[f"slopedea_{name}"] = df[f"slopediff_{name}"] - my_best_ec(df[f"slopediff_{name}"], smfreq)

    df[f"slope_{name}"] = 0
    df.loc[(df[f"slope1_{name}"] > df[f"slope2_{name}"]) & (df[f"slope1_{name}"] > 0), f"slope_{name}"] = 10
    df.loc[(df[f"slope1_{name}"] <= df[f"slope2_{name}"]) & (df[f"slope1_{name}"] <= 0), f"slope_{name}"] = -10


def macd_tor(df, abase, sfreq):
    """
    is not very useful since price/vol relationship is rather random
    So even if price and volume deviates/converges, it doesnt say anything about the future price
    """

    name = f"{abase}.vol.{sfreq}"

    df[f"abase_{name}"] = zlema((df[abase]), sfreq, 1.8)
    df[f"tor_{name}"] = zlema((df["turnover_rate"]), sfreq, 1.8)
    #
    # df[f"abase_{name}"] = df[abase] - highpass(df[abase], int(sfreq))
    # df[f"tor_{name}"] = df[abase] - highpass(df[abase], int(sfreq))

    df[f"macd_tor_diff{name}"] = df[f"abase_{name}"] - df[f"tor_{name}"]
    df[f"macd_tor_diff{name}"] = df[f"macd_tor_diff{name}"] * 1

    df[f"macd_tor_dea_{name}"] = df[f"macd_tor_diff{name}"] - supersmoother_3p(df[f"macd_tor_diff{name}"], int(sfreq / 2))
    df[f"macd_tor_dea_{name}"] = df[f"macd_tor_dea_{name}"] * 1

    df.loc[(df[f"macd_tor_dea_{name}"] > 0), f"macd_tor_{name}"] = 80
    df.loc[(df[f"macd_tor_dea_{name}"] <= 0), f"macd_tor_{name}"] = -80

    df[f"macd_tor_{name}"] = df[f"macd_tor_{name}"].fillna(method="ffill")

    return [f"macd_tor_{name}", f"macd_tor_diff{name}", f"macd_tor_dea_{name}"]


def my_macd(df, abase, sfreq, bfreq, type=1, score=10):
    """ using ehlers zero lag EMA used as MACD cross over signal instead of conventional EMA
        on daily chart, useable freqs are 12*60, 24*60 ,5*60

        IMPORTNAT:
        Use a very responsive indicator for EMA! Currently, ema is the most responsive
        Use a very smoother indicator for smooth! Currently, Supersmoother 3p is the most smoothest.
        NOT other way around
        Laguerre filter is overall very good, but is neither best at any discipline. Hence using EMA+ supersmoother 3p is better.
        Butterwohle is also very smooth, but it produces 1 more curve at turning point. Hence super smoother is better for this job.


        Works good on high volatile time, works bad on flat times.
        TODO I need some indicator to have high volatility in flat time so I can use this to better identify trend with macd
        """
    name = f"{abase}.{type, sfreq, bfreq,type}"
    df[f"zldif_{name}"] = 0
    df[f"zldea_{name}"] = 0
    if type == 0:  # standard macd with ma. conventional ma is very slow
        df[f"ema1_{name}"] = df[abase].rolling(sfreq).mean()
        df[f"ema2_{name}"] = df[abase].rolling(bfreq).mean()
        df[f"zldif_{name}"] = df[f"ema1_{name}"] - df[f"ema2_{name}"]
        df[f"zldiff_ss_big_{name}"] = supersmoother_3p(df[f"zldif_{name}"], int(sfreq / 2))
        df[f"zldea_{name}"] = df[f"zldif_{name}"] - df[f"zldiff_ss_big_{name}"]
        df.loc[(df[f"zldea_{name}"] > 0), f"zlmacd_{name}"] = score
        df.loc[(df[f"zldea_{name}"] < 0), f"zlmacd_{name}"] = -score
    if type == 1:  # standard macd but with zlema
        df[f"ema1_{name}"] = zlema((df[abase]), sfreq, 1.8)
        df[f"ema2_{name}"] = zlema((df[abase]), bfreq, 1.8)
        df[f"zldif_{name}"] = df[f"ema1_{name}"] - df[f"ema2_{name}"]
        df[f"zldiff_ss_big_{name}"] = supersmoother_3p(df[f"zldif_{name}"], int(sfreq))
        df[f"zldea_{name}"] = df[f"zldif_{name}"] - df[f"zldiff_ss_big_{name}"]
        df.loc[(df[f"zldea_{name}"] > 0), f"zlmacd_{name}"] = score
        df.loc[(df[f"zldea_{name}"] < 0), f"zlmacd_{name}"] = -score
    elif type == 2:  # macd where price > ema1 and ema2
        df[f"ema1_{name}"] = zlema((df[abase]), sfreq, 1.8)
        df[f"ema2_{name}"] = zlema((df[abase]), bfreq, 1.8)
        df.loc[(df[abase] > df[f"ema1_{name}"]) & (df[abase] > df[f"ema2_{name}"]), f"zlmacd_{name}"] = score
        df.loc[(df[abase] < df[f"ema1_{name}"]) & (df[abase] < df[f"ema2_{name}"]), f"zlmacd_{name}"] = -score
    elif type == 3:  # standard macd : ema1 > ema2. better than type 2 because price is too volatile
        df[f"ema1_{name}"] = zlema((df[abase]), sfreq, 1.8)
        df[f"ema2_{name}"] = zlema((df[abase]), bfreq, 1.8)
        df.loc[(df[f"ema1_{name}"] > df[f"ema2_{name}"]), f"zlmacd_{name}"] = score
        df.loc[(df[f"ema1_{name}"] < df[f"ema2_{name}"]), f"zlmacd_{name}"] = -score
    elif type == 4:  # macd with lowpass constructed from highpass. This basically replaces abv_ma
        df[f"ema1_{name}"] = df[abase] - highpass(df[abase], int(sfreq))
        df[f"ema2_{name}"] = df[abase] - highpass(df[abase], int(bfreq))
        df.loc[(df[f"ema1_{name}"] > df[f"ema2_{name}"]), f"zlmacd_{name}"] = score
        df.loc[(df[f"ema1_{name}"] < df[f"ema2_{name}"]), f"zlmacd_{name}"] = -score

        # patch other
        # df.loc[(df[f"ema1_{name}"] < df[f"ema2_{name}"]) & (df[f"ema1_{name}"] > df[f"ma120"]) & (df[f"ema2_{name}"] > df["ma120"]) , f"zlmacd_{name}"] = score
        # df.loc[(df[f"ema1_{name}"] > df[f"ema2_{name}"]) & (df[f"ema1_{name}"] < df[f"ma120"]) & (df[f"ema2_{name}"] < df["ma120"]) , f"zlmacd_{name}"] = -score

    elif type == 5:  # price and tor
        df[f"ema1_{name}"] = zlema((df[abase]), sfreq, 1.8)
        df[f"ema2_{name}"] = zlema((df["turnover_rate"]), sfreq, 1.8)
        df[f"zldif_{name}"] = df[f"ema1_{name}"] - df[f"ema2_{name}"]
        df[f"zldea_{name}"] = df[f"zldif_{name}"] - supersmoother_3p(df[f"zldif_{name}"], int(sfreq))
        df.loc[(df[f"zldea_{name}"] > 0), f"zlmacd_{name}"] = score
        df.loc[(df[f"zldea_{name}"] <= 0), f"zlmacd_{name}"] = -score
    df[f"zlmacd_{name}"] = df[f"zlmacd_{name}"].fillna(method="ffill")
    return [f"zlmacd_{name}", f"ema1_{name}", f"ema2_{name}", f"zldif_{name}", f"zldea_{name}"]


def my_ismax(df, abase, q=0.95, score=10):
    """
    the bigger the difference abase/e_max, the closer they are together. the smaller the difference they far away they are
    """
    name = f"{abase}"
    df[f"ismax_{name}"] = (df[abase] / df["e_max"]).between(q, q + 0.05).astype(int) * score
    df[f"ismax_{name}"] = df[f"ismax_{name}"].replace(to_replace=0, value=-score)
    return [f"ismax_{name}", ]


def my_ismin(df, abase, q=0.95, score=10):
    """
    the bigger the difference emin/abase, the closer they are together. the smaller the difference they far away they are
    """
    name = f"{abase}"
    df[f"ismin_{name}"] = (df["e_min"] / df[abase]).between(q, q + 0.05).astype(int) * score
    df[f"ismin_{name}"] = df[f"ismin_{name}"].replace(to_replace=0, value=-score)
    return [f"ismin_{name}", ]


def auto(df, abase, q_low=0.2, q_high=0.4, norm_freq=240, type=1, score=10):
    """can be used on any indicator
    gq=Generic quantile
    0. create an oscilator of that indicator
    1. create expanding mean of that indicator
    2. create percent=today_indicator/e_indicator
    3. assign rolling quantile quantile of percent

    This appoach needs to be mean stationary !!!! otherwise quantile makes nosense
    """
    #init
    name = f"{abase}.auto{norm_freq}.type{type}"
    if f"norm_{name}" not in df.columns:
        #3 choices. cg_oscilator, rsi, (today-yesterday)/today
        if type==1:
            df[f"norm_{name}"]= cg_Oscillator(df[abase], norm_freq)
        elif type==2:
            df[f"norm_{name}"]=talib.RSI(df[abase], norm_freq)
        elif type==3:
            #this is the same as ROCP rate of change percent
            df[f"norm_{name}"]= (df[abase]-df[abase].shift(1))/df[abase].shift(1)
        elif type==4:
            df[f"norm_{name}"]= df[abase].pct_change(norm_freq)

    #create expanding quantile
    for q in [q_low, q_high]:
        if f"q{q}_{name}" not in df.columns:
            df[f"q{q}_{name}"] = df[f"norm_{name}"].expanding(240).quantile(q)

    #assign todays value to a quantile
    df[f"in_q{q_low, q_high}_{name}"]=((df[f"q{q_low}_{name}"] <= df[f"norm_{name}"]) & (df[f"norm_{name}"] < df[f"q{q_high}_{name}"])).astype(int)*score
    df[f"in_q{q_low, q_high}_{name}"] = df[f"in_q{q_low, q_high}_{name}"].replace(to_replace=0, value=-score)
    return [f"in_q{q_low, q_high}_{name}", ]












def find_peaks_array(s, n=60):
    # Generate a noisy AR(1) sample
    np.random.seed(0)
    xs = [0]
    for r in s:
        xs.append(xs[-1] * 0.9 + r)
    df = pd.DataFrame(xs, columns=[s.name])
    # Find local peaks
    df[f'bot{n}'] = df.iloc[argrelextrema(df[s.name].values, np.less_equal, order=n)[0]][s.name]
    df[f'peak{n}'] = df.iloc[argrelextrema(df[s.name].values, np.greater_equal, order=n)[0]][s.name]
    df[f"bot{n}"].update(df[f"peak{n}"].notna())
    return df[f"bot{n}"]



def extrema_helper(df, abase, distance=1, height="", order=20, signal=100):
    from scipy.signal import argrelmin,argrelmax,peak_prominences

    def outlier_remove(array, n_neighbors=20, match=1):
        from sklearn.neighbors import LocalOutlierFactor

        X = [[x] for x in array]
        clf = LocalOutlierFactor(n_neighbors=n_neighbors)
        a_predict = clf.fit_predict(X)

        a_result = []
        for predict, value in zip(a_predict, array):
            print(f"predict", predict, value)
            if predict == match:
                a_result.append(value)
        return a_result
    """
    rules
    0. Basically: Starting a new trend requires BOTH high and low to be consistent
    1. If only one deviates, it continues the previous trend.
    2. the result is a signal that is very safe and does not take risk.
    
    
    1. only one outlier allowed. if second time the low is not strictly higher than last one, it a downtrend.
    2. if A extrema has no confirmation, and the B has 2. B dominates
    3. Extrema with the most recent information dominates
    
    """

    #init
    x = df[abase]
    lp= df["lp"]

    #peaks, _ = find_peaks(x,prominence=0,width=60)
    bottom = argrelmin(x.to_numpy(),order=order)[0]
    peaks = argrelmax(x.to_numpy(),order=order)[0]

    #data cleaning
    bottom_noutlier=outlier_remove(bottom,n_neighbors=20,match=1)
    bottom_outlier=outlier_remove(bottom,n_neighbors=2,match=-1)

    #prominence in case needed
    prominences = peak_prominences(x, peaks)[0]
    contour_heights = x[peaks] - prominences

    #1. iteration assign value/pct_chg of extrema
    for counter,(label, extrema) in enumerate({"bott":bottom,"peakk":peaks}.items()):
        df[f"{label}_pvalue"]=df.loc[extrema,"close"]
        df[f"{label}_fvalue"]=df[f"{label}_pvalue"].fillna(method="ffill")
        df[f"{label}_value_pct_chg"]=df[f"{label}_fvalue"].pct_change()

    h_peak = df[f"peakk_value_pct_chg"]
    h_bott = df[f"bott_value_pct_chg"]

    #2. iteration assign signal
    for counter, (label, extrema) in enumerate({"bott": bottom, "peakk": peaks}.items()):
        df[f"{label}_diff"]=0

        #for now the peak and bott are actually the SAME
        if label =="peakk":
            df.loc[ (h_peak>0.05) | (df["close"]/df[f"peakk_fvalue"] >1.05) ,f"{label}_diff"]=signal  # df["bott_diff"]=df["bott_ffill"].diff()*500
            df.loc[ (h_bott<-0.05) | (df["close"] / df[f"bott_fvalue"]<0.95) ,f"{label}_diff"]=-signal  # df["bott_diff"]=df["bott_ffill"].diff()*500
        elif label=="bott":
            df.loc[(h_peak > 0.05) | (df["close"]/df[f"peakk_fvalue"] >1.05), f"{label}_diff"] = signal  # df["bott_diff"]=df["bott_ffill"].diff()*500
            df.loc[(h_bott < -0.05) | (df["close"] / df[f"bott_fvalue"]<0.95), f"{label}_diff"] = -signal  # df["bott_diff"]=df["bott_ffill"].diff()*500

        df[f"{label}_diff"]=df[f"{label}_diff"].replace(0,np.nan).fillna(method="ffill")

    #simualte past iteration
    matplotlib.use("TkAgg")
    for counter,(index,df) in enumerate(LB.custom_expand(df,1000).items()):
        if counter%20!=0:
            continue

        print(counter,index)

        #array of extrema without nan = shrink close only to extrema
        s_bott_pvalue=df["bott_pvalue"].dropna()
        s_peakk_pvalue=df["peakk_pvalue"].dropna()

        dict_residuals_bott={}
        dict_residuals_peakk={}
        dict_regression_bott={}
        dict_regression_peakk={}

        # do regression with extrema with all past extrema. The regression with lowest residual wins
        for counter,_ in enumerate(s_bott_pvalue):
            if counter >3:

                #bott
                s_part_pvalue=s_bott_pvalue.tail(counter)
                distance=index - s_part_pvalue.index[0]
                #s_part_pvalue[index]=df.at[index,"close"]
                s_bott_lg,residual=LB.get_linear_regression_s_full(s_part_pvalue.index,s_part_pvalue)
                dict_residuals_bott[counter]=residual/distance**2
                dict_regression_bott[counter]=(s_part_pvalue,s_bott_lg)

                #peak
                s_part_pvalue = s_peakk_pvalue.tail(counter)
                distance = index - s_part_pvalue.index[0]
                #s_part_pvalue[index] = df.at[index, "close"]
                s_bott_lg, residual = LB.get_linear_regression_s_full(s_part_pvalue.index, s_part_pvalue)
                dict_residuals_peakk[counter] = residual / distance**2
                dict_regression_peakk[counter] = (s_part_pvalue, s_bott_lg)

        #find the regression with least residual
        from operator import itemgetter
        n=1
        dict_min_residuals_bott = dict(sorted(dict_residuals_bott.items(), key = itemgetter(1), reverse = True)[-n:])
        dict_min_residuals_peakk = dict(sorted(dict_residuals_bott.items(), key = itemgetter(1), reverse = True)[-n:])

        #plot them
        for key,residual in dict_min_residuals_bott.items():
            _,s_bott_lg=dict_regression_bott[key]
            plt.plot(s_bott_lg)

        for key, residual in dict_min_residuals_peakk.items():
            _,s_peakk_lg=dict_regression_peakk[key]
            plt.plot(s_peakk_lg)

        #plot chart
        plt.plot(df["close"])
        #plt.show()
        plt.savefig(f"tesplot/{index}.jpg")
        plt.clf()
        plt.close()

    #add macd signal for comparison
    label=my_macd(df=df,sfreq=360,bfreq=500,abase="close",type=4,score=signal)
    label=label[0]

    plt.plot(x)
    plt.plot(df[label])

    plt.plot(df["bott_diff"])
    plt.plot(df["peakk_diff"])

    plt.plot(df["bott_pvalue"],"1")
    plt.plot(df["peakk_pvalue"],"1")

    plt.show()


def my_find_peakks(df, abase, a_n=[60]):
    """
    Strengh of resistance support are defined by:
    1. how long it remains a resistance or support (remains good for n = 20,60,120,240?)
    2. How often the price can not break through it. (occurence)
    """
    # Generate a noisy AR(1) sample
    a_bot_name = []
    a_peak_name = []
    np.random.seed(0)
    s = df[abase]
    xs = [0]
    for r in s:
        xs.append(xs[-1] * 0.9 + r)
    df = pd.DataFrame(xs, columns=[s.name])
    for n in a_n:
        # Find local peaks
        df[f'bot{n}'] = df.iloc[argrelextrema(df[s.name].values, np.less_equal, order=n)[0]][s.name]
        df[f'peak{n}'] = df.iloc[argrelextrema(df[s.name].values, np.greater_equal, order=n)[0]][s.name]
        a_bot_name.append(f'bot{n}')
        a_peak_name.append(f'peak{n}')

    # checks strenght of a maximum and miminum
    df["support_strengh"] = df[a_bot_name].count(axis=1)
    df["resistance_strengh"] = df[a_peak_name].count(axis=1)

    # puts all maxima and minimaxs togehter
    d_all_rs = {}
    for n in a_n:
        d_value_index_pairs = df.loc[df[f'bot{n}'].notna(), f'bot{n}'].to_dict()
        d_all_rs.update(d_value_index_pairs)

        d_value_index_pairs = df.loc[df[f'peak{n}'].notna(), f'peak{n}'].to_dict()
        d_all_rs.update(d_value_index_pairs)

    d_final_rs = {}
    for index_1, value_1 in d_all_rs.items():
        keep = True
        for index_2, value_2 in d_final_rs.items():
            closeness = value_2 / value_1
            if 0.95 < closeness < 1.05:
                keep = False
        if keep:
            d_final_rs[index_1] = value_1

    # count how many rs we have. How many support is under price, how many support is over price
    df["total_support_resistance"] = 0
    df["abv_support"] = 0
    df["und_resistance"] = 0
    a_rs_names = []
    for counter, (resistance_index, resistance_val) in enumerate(d_final_rs.items()):
        print("unique", resistance_index, resistance_val)
        df.loc[df.index >= resistance_index, f"rs{counter}"] = resistance_val
        a_rs_names.append(f"rs{counter}")
        if counter == 23:
            df.loc[(df["close"] / df[f"rs{counter}"]).between(0.98, 1.02), f"rs{counter}_challenge"] = 100
            df[f"rs{counter}_challenge"] = df[f"rs{counter}_challenge"].fillna(0)

        df["total_support_resistance"] = df["total_support_resistance"] + (df[f"rs{counter}"].notna()).astype(int)
        df["abv_support"] = df["abv_support"] + (df["close"] > df[f"rs{counter}"]).astype(int)
        df["und_resistance"] = df["und_resistance"] + (df["close"] < df[f"rs{counter}"]).astype(int)

    a_trend_name = []
    for index1, index2 in LB.custom_pairwise_overlap([*d_final_rs]):
        print(f"pair {index1, index2}")
        value1 = d_final_rs[index1]
        value2 = d_final_rs[index2]
        df.loc[df.index == index1, f"{value1, value2}"] = value1
        df.loc[df.index == index2, f"{value1, value2}"] = value2
        df[f"{value1, value2}"] = df[f"{value1, value2}"].interpolate()
        a_trend_name.append(f"{value1, value2}")

    # Create trend support resistance lines using two max and two mins
    df.to_csv("test.csv")

    # Plot results
    # plt.scatter(df.index, df['min'], c='r')
    # plt.scatter(df.index, df['max'], c='g')
    df[["close"] + a_rs_names + a_trend_name + ["total_support_resistance", "abv_support", "und_resistance", "rs23_challenge"]].plot(legend=True)
    plt.show()


def find_flat(df, abase):
    """
    go thorugh ALL possible indicators and COMBINE them together to an index that defines up, down trend or no trend.

    cast all indicator to 3 values: -1, 0, 1 for down trend, no trend, uptrend.

    """
    a_freq = [240]
    df["ma20"] = df[abase].rolling(20).mean()
    a_stable = []

    # unstable period
    # momentum
    df[f"bop"] = talib.BOP(df["open"], df["high"], df["low"], df["close"])  # -1 to 1

    # volume
    df[f"ad"] = talib.AD(df["high"], df["low"], df["close"], df["vol"])
    df[f"obv"] = talib.OBV(df["close"], df["vol"])
    a_unstable = ["bop", "ad", "obv"]
    # stable period
    for freq in a_freq:
        df[f"rsi{freq}"] = talib.RSI(df[abase], timeperiod=freq)

        """ idea: 
        1.average direction of past freq up must almost be same as average direction of past freq down. AND price should stay somewhat the same.
        2. count the peak and bot value of an OSCILATOR. IF last peak and bot are very close, then probably flat time
        """

        # MOMENTUM INDICATORS
        """ok 0 to 100, rarely over 60 https://www.fmlabs.com/reference/ADX.htm similar to dx"""
        df[f"adx{freq}"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=freq)
        df.loc[df[f"adx{freq}"] < 6, f"adx{freq}_trend"] = 0
        df.loc[df[f"adx{freq}"] > 6, f"adx{freq}_trend"] = 10

        """osci too hard difference between two ma, not normalized. need to normalize first https://www.fmlabs.com/reference/default.htm?url=PriceOscillator.htm"""
        df[f"apo{freq}"] = talib.APO(df["close"], freq, freq * 2)
        df[f"apo{freq}_trend"] = 10
        df.loc[(df[f"apo{freq}"].between(-1, 1)) & (df[f"apo{freq}"].shift(int(freq / 2)).between(-2, 2)), f"apo{freq}_trend"] = 0

        """osci too hard -100 to 100 https://www.fmlabs.com/reference/default.htm?url=AroonOscillator.htm"""
        df[f"aroonosc{freq}"] = talib.AROONOSC(df["high"], df["low"], freq)
        df[f"aroonosc{freq}_trend"] = 10
        df.loc[df[f"aroonosc{freq}"].between(-70, 70), f"aroonosc{freq}_trend"] = 0

        """osci too hard -100 to 100 https://www.fmlabs.com/reference/default.htm?url=CCI.htm"""
        df[f"cci{freq}"] = talib.CCI(df["high"], df["low"], df["close"], freq)  # basically modified rsi
        df[f"cci{freq}_trend"] = 10
        df.loc[df[f"cci{freq}"].between(-70, 70), f"cci{freq}_trend"] = 0

        """osci too hard 0 to 100 but rarely over 60 https://www.fmlabs.com/reference/default.htm?url=CMO.htm"""
        df[f"cmo{freq}"] = talib.CMO(df["close"], freq)  # -100 to 100
        df[f"cmo{freq}_trend"] = 10
        df.loc[df[f"cmo{freq}"].between(-70, 70), f"cmo{freq}_trend"] = 0

        """osci too hard 0 to 100 https://www.fmlabs.com/reference/default.htm?url=DX.htm"""
        df[f"dx{freq}"] = talib.DX(df["high"], df["low"], df["close"], timeperiod=freq)
        df[f"dx{freq}_trend"] = 10
        df.loc[df[f"dx{freq}"].between(-70, 70), f"dx{freq}_trend"] = 0

        """0 to 100 https://www.fmlabs.com/reference/default.htm?url=MFI.htm"""
        df[f"mfi{freq}"] = talib.MFI(df["high"], df["low"], df["close"], df["vol"], timeperiod=freq)
        df[f"mfi{freq}_trend"] = 10
        df.loc[df[f"mfi{freq}"].between(-70, 70), f"mfi{freq}_trend"] = 0

        """https://www.fmlabs.com/reference/default.htm?url=DI.htm"""
        df[f"minus_di{freq}"] = talib.MINUS_DI(df["high"], df["low"], df["close"], timeperiod=freq)
        df[f"plus_di{freq}"] = talib.PLUS_DI(df["high"], df["low"], df["close"], timeperiod=freq)

        """no doc"""
        df[f"minus_dm{freq}"] = talib.MINUS_DM(df["high"], df["low"], timeperiod=freq)
        df[f"plus_dm{freq}"] = talib.PLUS_DM(df["high"], df["low"], timeperiod=freq)

        """abs value, not relative http://www.fmlabs.com/reference/Momentum.htm"""
        df[f"mom{freq}"] = talib.MOM(df["close"], timeperiod=freq)

        """http://www.fmlabs.com/reference/PriceOscillatorPct.htm"""
        df[f"ppo{freq}"] = talib.PPO(df["close"], freq, freq * 2)
        df["test"] = find_peaks_array(df[f"ppo{freq}"], freq)
        df["test"] = df["test"].fillna(method="ffill")
        print(df["test"].notna())

        """http://www.fmlabs.com/reference/PriceOscillatorPct.htm"""
        df[f"roc{freq}"] = talib.ROC(df["close"], freq)

        """0 to 100 rsi"""
        df[f"rsi{freq}"] = talib.RSI(df["close"], freq)
        df[f"rsi{freq}"] = supersmoother_3p(df[f"rsi{freq}"], int(freq / 4))
        df[f"rsi{freq}_diff"] = df[f"rsi{freq}"].diff()

        df[f"rsi{freq}_trend"] = 10
        df.loc[(df[f"rsi{freq}"].between(-48, 52)) & (df[f"rsi{freq}_diff"].between(-0.3, 0.3)), f"rsi{freq}_trend"] = 0

        """ """
        df[f"stochrsi_fastk{freq}"], df[f"stochrsi_fastd{freq}"] = talib.STOCHRSI(df["close"], freq, int(freq / 2), int(freq / 3))

        """http://www.fmlabs.com/reference/PriceOscillatorPct.htm"""
        df[f"ultiosc{freq}"] = talib.ULTOSC(df["high"], df["low"], df["close"], int(freq / 2), freq, int(freq * 2))

        """http://www.fmlabs.com/reference/PriceOscillatorPct.htm"""
        df[f"willr{freq}"] = talib.WILLR(df["high"], df["low"], df["close"], freq)

        # VOLUME INDICATORS
        df[f"adosc{freq}"] = talib.ADOSC(df["high"], df["low"], df["close"], df["vol"], freq, freq * 3)

        # volatility indicators
        df[f"atr{freq}"] = talib.ATR(df["high"], df["low"], df["close"], freq)
        df[f"atr_helper{freq}"] = df[f"atr{freq}"].rolling(60).mean()

        df[f"rsi{freq}_true"] = (df[f"rsi{freq}"].between(45, 55)).astype(int)
        df[f"adx{freq}_true"] = (df[f"adx{freq}"] < 10).astype(int)
        df[f"atr{freq}_true"] = (df[f"atr{freq}"] < df[f"atr_helper{freq}"]).astype(int)

    df[f"flat{freq}"] = (df[f"rsi{freq}_true"] + df[f"adx{freq}_true"] + df[f"atr{freq}_true"]) * 10

    a_stable = a_stable + [f"adx{freq}", f"adx{freq}_trend"]

    df[["close"] + a_stable].plot(legend=True)
    plt.show()





# generate test for all fund stock index and for all strategy and variables.
# a_freqs=[5, 10, 20, 40, 60, 80, 120, 160, 200, 240, 360, 500, 750],
def atest(asset="E", step=1, d_queries={}, kwargs={"func": my_macd, "fname": "macd_for_all", "a_kwargs": [{}, {}, {}, {}]}):
    """
    This is a general statistic test creator
    1. provide all cases
    2. The little difference between this and brute force: bruteforce only creates indicator, but not assign buy/sell signals with 10 or -10
    Variables on how to loop over are in the function. apply function variables are in the dict kwargs
    """
    d_preload = DB.preload(asset=asset, step=step, period_abv=240, d_queries_ts_code=d_queries)

    for one_kwarg in kwargs["a_kwargs"]:
        param_string = '_'.join([f'{key}{value}' for key, value in one_kwarg.items()])
        a_path = LB.a_path(f"Market/CN/Atest/{kwargs['fname']}/{one_kwarg['abase']}/{asset}_step{step}_{kwargs['fname']}_{param_string}")
        if os.path.exists(a_path[0]):
            print(f"path exists: {a_path[0]}")
            continue

        df_result = pd.DataFrame()
        for counter, (ts_code, df_asset) in enumerate(d_preload.items()):
            print(f"{counter}: asset:{asset}, {ts_code}, step:{step}, {kwargs['fname']}, {one_kwarg}")

            try:
                func_return_column = kwargs["func"](df=df_asset, **one_kwarg)[0]

                """could also add pearson, but since outcome is binary, no need for pearson"""
                df_asset["tomorrow1"] = 1 + df_asset["open.fgain1"].shift(-1)  # one day delayed signal. today signal, tomorrow buy, atomorrow sell
                df_result.at[ts_code, "period"] = len(df_asset)
                df_result.at[ts_code, "gmean"] = asset_gmean = gmean(df_asset["tomorrow1"].dropna())
                df_result.at[ts_code, "sharp"] = asset_sharp = (df_asset["tomorrow1"]).mean()/(df_asset["tomorrow1"]).std()
                df_result.at[ts_code, "general_daily_winrate"] = ((df_asset["tomorrow1"] > 1).astype(int)).mean()

                df_macd_buy = df_asset[df_asset[func_return_column] == one_kwarg["score"]]
                df_result.at[ts_code, "uptrend_gmean"] = gmean(df_macd_buy["tomorrow1"].dropna()) / asset_gmean
                df_result.at[ts_code, "uptrend_sharp"] = (df_macd_buy["tomorrow1"].mean()) / (df_macd_buy["tomorrow1"].std()) /asset_sharp
                df_result.at[ts_code, "uptrend_daily_winrate"] = ((df_macd_buy["tomorrow1"] > 1).astype(int)).mean()
                df_result.at[ts_code, "uptrend_occ"] = len(df_macd_buy)/len(df_asset)

                df_macd_sell = df_asset[df_asset[func_return_column] == -one_kwarg["score"]]
                df_result.at[ts_code, "downtrend_gmean"] = gmean(df_macd_sell["tomorrow1"].dropna()) / asset_gmean
                df_result.at[ts_code, "downtrend_sharp"] = (df_macd_sell["tomorrow1"].mean()) / (df_macd_sell["tomorrow1"].std()) / asset_sharp
                df_result.at[ts_code, "downtrend_daily_winrate"] = ((df_macd_sell["tomorrow1"] > 1).astype(int)).mean()
                df_result.at[ts_code, "downtrend_occ"] = len(df_macd_sell) / len(df_asset)
            except Exception as e:
                print("exception at func execute", e)
                continue

        # important check only if up/downtrend_gmean are not nan. Which means they actually exist for this strategy.
        df_result.loc[df_result["uptrend_gmean"].notna(), "up_better_mean"] = (df_result.loc[df_result["uptrend_gmean"].notna(), "uptrend_gmean"] > df_result.loc[df_result["uptrend_gmean"].notna(), "gmean"]).astype(int)
        df_result.loc[df_result["downtrend_gmean"].notna(), "down_better_mean"] = (df_result.loc[df_result["downtrend_gmean"].notna(), "downtrend_gmean"] > df_result.loc[df_result["downtrend_gmean"].notna(), "gmean"]).astype(int)
        df_result["up_down_gmean_diff"] = df_result["uptrend_gmean"] - df_result["downtrend_gmean"]
        LB.to_csv_feather(df=df_result,a_path=a_path, skip_feather=True)
        # very slow witgh DB.to_excel_with_static_data(df_ts_code=df_result, path=path, sort=[])

    # create summary for all
    df_summary = pd.DataFrame()
    df_uptrend_gmean = pd.DataFrame()
    df_downtrend_gmean = pd.DataFrame()
    df_up_better_mean = pd.DataFrame()
    df_down_better_mean = pd.DataFrame()
    abase=one_kwarg['abase'] #abase should not change during iteration.otherwise unstable
    for one_kwarg in kwargs["a_kwargs"]:
        param_string = '_'.join([f'{key}{value}' for key, value in one_kwarg.items()])
        a_path =LB.a_path( f"Market/CN/Atest/{kwargs['fname']}/{one_kwarg['abase']}/{asset}_step{step}_{kwargs['fname']}_{param_string}")

        print(f"summarizing {a_path[0]}")
        df_macd = pd.read_csv(a_path[0])
        df_summary.at[a_path[0], "gmean"] = df_macd["gmean"].mean()
        df_summary.at[a_path[0], "general_daily_winrate"] = df_macd["general_daily_winrate"].mean()
        df_summary.at[a_path[0], "uptrend_gmean"] = uptrend_gmean = df_macd["uptrend_gmean"].mean()
        df_summary.at[a_path[0], "uptrend_daily_winrate"] = df_macd["uptrend_daily_winrate"].mean()
        df_summary.at[a_path[0], "uptrend_occ"]=df_macd["uptrend_occ"].mean()
        df_summary.at[a_path[0], "downtrend_gmean"] = downtrend_gmean = df_macd["downtrend_gmean"].mean()
        df_summary.at[a_path[0], "downtrend_daily_winrate"] = df_macd["downtrend_daily_winrate"].mean()
        df_summary.at[a_path[0], "downtrend_occ"] = df_macd["downtrend_occ"].mean()
        df_summary.at[a_path[0], "up_better_mean"] = up_better_mean = df_macd["up_better_mean"].mean()
        df_summary.at[a_path[0], "down_better_mean"] = down_better_mean = df_macd["down_better_mean"].mean()
        df_summary.at[a_path[0], "up_down_gmean_diff"] = df_macd["up_down_gmean_diff"].mean()

        # create heatmap only if two frequencies are involved in creation
        #if up/downtrend exists, is it better than mean?
        if "sfreq" in one_kwarg and "bfreq" in one_kwarg:
            df_uptrend_gmean.at[f"{one_kwarg['sfreq']}_abv", one_kwarg["bfreq"]] = uptrend_gmean
            df_downtrend_gmean.at[f"{one_kwarg['sfreq']}_abv", one_kwarg["bfreq"]] = downtrend_gmean
            df_up_better_mean.at[f"{one_kwarg['sfreq']}_abv", one_kwarg["bfreq"]] = up_better_mean
            df_down_better_mean.at[f"{one_kwarg['sfreq']}_abv", one_kwarg["bfreq"]] = down_better_mean
        elif kwargs['fname']== "my_gq":
            df_uptrend_gmean.at[f"norm_freq{one_kwarg['norm_freq']}", f"{one_kwarg['q_low'],one_kwarg['q_high']}"] = uptrend_gmean
            df_downtrend_gmean.at[f"norm_freq{one_kwarg['norm_freq']}", f"{one_kwarg['q_low'],one_kwarg['q_high']}"] = downtrend_gmean
            df_up_better_mean.at[f"norm_freq{one_kwarg['norm_freq']}", f"{one_kwarg['q_low'],one_kwarg['q_high']}"] = up_better_mean
            df_down_better_mean.at[f"norm_freq{one_kwarg['norm_freq']}", f"{one_kwarg['q_low'],one_kwarg['q_high']}"] = down_better_mean

    d_summary = {"Overview": df_summary}
    d_summary["uptrend_gmean"] = df_uptrend_gmean
    d_summary["downtrend_gmean"] = df_downtrend_gmean
    d_summary["up_better_mean"] = df_up_better_mean
    d_summary["down_better_mean"] = df_down_better_mean
    LB.to_excel(path=f"Market/CN/Atest/{kwargs['fname']}/{abase}/summary_{asset}_step{step}_{kwargs['fname']}_{param_string}.xlsx", d_df=d_summary)


def atest_manu(fname="macd", a_abase=["close"]):

    for abase in a_abase:

        #setting generation
        a_kwargs = []
        if fname == "macd":
            func = my_macd
            d_steps = {"F": 1, "FD": 2, "G": 1, "I": 2, "E": 6}
            for sfreq, bfreq in LB.custom_pairwise_combination([5, 10, 20, 40, 60, 80, 120, 180, 240, 320, 400, 480], 2):
                if sfreq < bfreq:
                    a_kwargs.append({"abase": abase, "sfreq": sfreq, "bfreq": bfreq, "type": 1, "score": 1})
        elif fname == "is_max":
            func = my_ismax
            d_steps = {"F": 1, "FD": 1, "G": 1, "I": 1, "E": 1}
            for q in np.linspace(0, 1,11):
                a_kwargs.append({"abase": abase, "q": q, "score": 1})
        elif fname == "is_min":
            func = my_ismin
            d_steps = {"F": 1, "FD": 1, "G": 1, "I": 1, "E": 1}
            for q in np.linspace(0, 1,11):
                a_kwargs.append({"abase": abase, "q": q, "score": 1})

        #run atest
        LB.print_iterables(a_kwargs)
        for asset in ["F","FD","G","I","E"]:
            atest(asset=asset, step=d_steps[asset], kwargs={"func": func, "fname": fname, "a_kwargs": a_kwargs}, d_queries=LB.c_G_queries() if asset=="G" else {})


def atest_auto(type=4):

    for asset in ["G"]: #,"FD","G","I","E"
        #get example column of this asset
        a_example_column = DB.get_example_column(asset=asset, numeric_only=True)
        # remove unessesary columns:
        a_columns = []
        for column in a_example_column:
            for exclude_column in ["fgain"]:
                if exclude_column not in column:
                    a_columns.append(column)

        for col in a_columns:
            #setting generation
            a_kwargs = []
            func = auto
            fname=func.__name__
            d_steps = {"F": 1, "FD": 1, "G": 1, "I": 1, "E": 2}
            for norm_freq in [5,10,20,60,120,240,500]:
                for q_low,q_high in LB.custom_pairwise_overlap(LB.drange(0,101,10)):
                    a_kwargs.append({"abase": col, "q_low": q_low, "q_high":q_high,"norm_freq":norm_freq,"score": 1,"type":type})

            #run atest
            LB.print_iterables(a_kwargs)
            atest(asset=asset, step=d_steps[asset], kwargs={"func": func, "fname": fname, "a_kwargs": a_kwargs}, d_queries=LB.c_G_queries() if asset=="G" else {})



def start_season(df, n=1, type="year"):
    """
    Hypothesis Question: if first n month return is positive, how likely is the whole year positive?

    1. convert day format to month format
    2. create month and year df
    3. merge together
    4. analyze pct_chg

    True_True, True_False,False_True, False_False are to determine the correct prediction
    Pearson, spearman are to predict the strengh of prediction
    """

    if type=="monthofyear": #1-12
        suffix1="_y"
        suffix2="_m"
        df_year=LB.timeseries_to_year(df)
        df_month = LB.timeseries_to_month(df)

        df_year["index_copy"]=df_year.index
        df_year["year"]=df_year["index_copy"].apply(lambda x: get_trade_date_datetime_y(x))  # can be way more efficient

        df_month["index_copy"] = df_month.index
        df_month["year"] = df_month["index_copy"].apply(lambda x: get_trade_date_datetime_y(x))  # can be way more efficient
        df_month["month"] = df_month["index_copy"].apply(lambda x: get_trade_date_datetime_m(x))  # can be way more efficient
        df_month=df_month[df_month["month"] == n]

        df_combined=pd.merge(df_year,df_month, on="year", how="left",suffixes=[suffix1,suffix2],sort=False)
    elif type=="seasonofyear": #1-4
        suffix1 = "_y"
        suffix2 = "_s"
        df_year = LB.timeseries_to_year(df)
        df_season = LB.timeseries_to_season(df)

        df_year["index_copy"] = df_year.index
        df_year["year"] = df_year["index_copy"].apply(lambda x: get_trade_date_datetime_y(x))  # can be way more efficient

        df_season["index_copy"] = df_season.index
        df_season["year"] = df_season["index_copy"].apply(lambda x: get_trade_date_datetime_y(x))  # can be way more efficient
        df_season["season"] = df_season["index_copy"].apply(lambda x: get_trade_date_datetime_s(x))  # can be way more efficient
        df_season = df_season[df_season["season"] == n]

        df_combined = pd.merge(df_year, df_season, on="year", how="left", suffixes=[suffix1, suffix2], sort=False)

        pass
    elif type=="weekofmonth":#1-6
        suffix1 = "_m"
        suffix2 = "_w"
        df_month = LB.timeseries_to_month(df)
        df_week = LB.timeseries_to_week(df)

        df_month["index_copy"] = df_month.index
        df_month["year"] = df_month["index_copy"].apply(lambda x: get_trade_date_datetime_y(x))  # can be way more efficient
        df_month["month"] = df_month["index_copy"].apply(lambda x: get_trade_date_datetime_m(x))  # can be way more efficient

        df_week["index_copy"] = df_week.index
        df_week["year"] = df_week["index_copy"].apply(lambda x: get_trade_date_datetime_y(x))  # can be way more efficient
        df_week["month"] = df_week["index_copy"].apply(lambda x: get_trade_date_datetime_m(x))  # can be way more efficient
        df_week["weekofmonth"] = df_week["index_copy"].apply(lambda x: get_trade_date_datetime_weekofmonth(x))  # can be way more efficient
        df_week = df_week[df_week["weekofmonth"] == n]

        df_combined = pd.merge(df_month, df_week, on=["year","month"], how="left", suffixes=[suffix1, suffix2], sort=False)


    elif type=="dayofweek": #1-5
        pass

    #many ways to determine that
    periods=len(df_combined)
    TT= len(df_combined[(df_combined[f"pct_chg{suffix2}"]>0) & (df_combined[f"pct_chg{suffix1}"]>0) ])/periods
    TF= len(df_combined[(df_combined[f"pct_chg{suffix2}"]>0) & (df_combined[f"pct_chg{suffix1}"]<0) ])/periods
    FT= len(df_combined[(df_combined[f"pct_chg{suffix2}"]<0) & (df_combined[f"pct_chg{suffix1}"]>0) ])/periods
    FF= len(df_combined[(df_combined[f"pct_chg{suffix2}"]<0) & (df_combined[f"pct_chg{suffix1}"]<0) ])/periods
    pearson=df_combined[f"pct_chg{suffix2}"].corr(df_combined[f"pct_chg{suffix1}"])
    spearman=df_combined[f"pct_chg{suffix2}"].corr(df_combined[f"pct_chg{suffix1}"],method="spearman")
    return pd.Series({"periods":periods,"TT":TT,"TF":TF,"FT":FT,"FF":FF,"pearson":pearson,"spearman":spearman})



def start_tester(asset="I", a_n=[1, 2, 3, 4,5,6,7,8,9,10,11,12], type="monthofyear"):

    if asset == "I":
        d_queries_ts_code={"I":["category != '债券指数' "]}
    elif asset=="G":
        d_queries_ts_code=LB.c_G_queries()
    else:
        d_queries_ts_code = {}

    d_preload=DB.preload(asset=asset,step=1,d_queries_ts_code=d_queries_ts_code)
    for n in a_n:
        a_path = LB.a_path(f"Market/CN/ATest/start_season/{type}/{asset}/n{n}")
        if not os.path.isfile(a_path[0]):
            a_result = []

            for ts_code, df_asset in d_preload.items():
                print(f"start_tester {ts_code} {n}")
                s=start_season(df=df_asset, n=n, type=type)
                s["ts_code"]=ts_code
                a_result.append(s)
            df_result=pd.DataFrame(a_result)
            LB.to_csv_feather(df=df_result,a_path=a_path)

    #summarizing summary
    a_result=[]
    for n in a_n:
        a_path = LB.a_path(f"Market/CN/ATest/start_season/{type}/{asset}/n{n}")
        df=DB.get(a_path,set_index="index")
        df=df.mean()
        a_result.append(df)
        print("load",a_path[0])
    df_result = pd.DataFrame(a_result)

    a_path=LB.a_path(f"Market/CN/ATest/start_season/{type}/{asset}/summary_{type}_{asset}")
    LB.to_csv_feather(df=df_result, a_path=a_path,skip_feather=True)



def prob_gain_asset(asset="E"):
    """
    Answers this question:
    1. If % of previous n days is up/down, what is probability for next n day to be up/down

    The goal is to predict the direction of the movement.
    A: the more previous days are down, the more likely future days are up
    """
    d_preload=DB.preload(asset=asset,step=10)
    for n in [3,4,5,6,10,20,40,60]:
        df_result=pd.DataFrame()
        df_heat=pd.DataFrame()
        path=f"Market/CN/Atest/prob_gain/{n}_summary.xlsx"

        if not os.path.isfile(path):
            for ts_code , df_asset in d_preload.items():
                print(f"prob_gain {n}: {ts_code}")

                #reset index to later easier calcualte days
                df_asset=df_asset.reset_index()

                df_asset["probgaingeneric"]=(df_asset["pct_chg"]>0).astype(int)
                df_asset[f"probggain_init{n}"] = df_asset["probgaingeneric"].rolling(n).sum()

                for subn in range(0,n+1):
                    #Mark day where % of past n days are positive = meet the criteria
                    df_asset[f"probggain_marker{n,subn}"]=0
                    df_asset.loc[df_asset[f"probggain_init{n}"]==subn,f"probggain_marker{n,subn}"]=1

                    df_filter=df_asset[df_asset[f"probggain_marker{n,subn}"]==1]
                    occurence=len(df_filter)/len(df_asset)
                    sharp_fgain5=df_filter["close.fgain5"].mean()/df_filter["close.fgain5"].std() if df_filter["close.fgain5"].std()!=0 else np.nan


                    #for each match day in df_filter, check out their next 5 days
                    a_pct_positive=[]
                    for index in df_filter.index:
                        df_part=df_asset.loc[index+1:index+6]
                        print(f"prob_gain {n}: {ts_code} {len(df_part)}")
                        if not df_part.empty:
                            pct_positive=len(df_part[df_part["pct_chg"]>0])/len(df_part)
                            a_pct_positive.append(pct_positive)


                    s_result=pd.Series(a_pct_positive)
                    positive=s_result.mean()

                    df_result.at[ts_code,f"{n,subn}_occ"]=occurence
                    df_result.at[ts_code, f"{n, subn}_pct_positive"] = positive
                    df_result.at[ts_code,f"{n,subn}_sharp_gain5"]=sharp_fgain5


            LB.to_excel(path=path,d_df={"Overview":df_result,"Heat":df_heat})




def extrema():
    """
    This test tries to combine two rules.
    1. The long term trend longer the better
    2. The price the lower the better

    This seems to be contradicting at first. But the idea is to buy stock have keep their current rend as low as possible.

    If trend goes down, loss limit. Else always go in and buy stocks with good trend.

    More details:
    1. How long is the trend in the past and how long for future?
    2. How strong is the trend?
    3.

    procedure:
    1. first find the last significant turning point(High/low) for that period
    2. check if close is in up or downtrend since then
    3. check from that turning point, smaller freq high/low.
    4. if highs are higher, lows are higher, then in uptrend.
    5. Slope of trend


    todo new method
    1. Calculate reverse from today on all high /lows and make regression on then. if the regression does not fit anymore. then the trend is the last strongest trend.
    A: Done that. the problem is tat trend exhange happens too often
    A: sometimes you have to skip last couple high/lows because they are a new trend
    """

    df_asset=DB.get_asset(ts_code="399001.SZ", asset="I")
    df_asset=LB.ohlcpp(df_asset)
    df_asset=df_asset.reset_index()

    df_asset["hp"]= highpass(df_asset["close"], 20)
    df_asset["lp"]=df_asset["close"]-df_asset["hp"]

    df_asset=extrema_helper(df_asset, "close", order=40, signal=3000)

def intraday_analysis():
    """
    The result of intraday analysis:
    -Highest deviation at first 15 min of trading day
    -Lowest deviation at last 15 min
    -if first 15 min are positive, there are 65% the whole day is positive
    """
    var = 15
    asset="I"
    for ts_code in ["000001.SH","399006.SZ","399001.SZ"]:
        df = pd.read_csv(f"D:\Stock\Market\CN\Asset\{asset}\{var}m/{ts_code}.csv")

        df["pct_chg"] = df["close"].pct_change()

        df["day"] = df["date"].str.slice(0, 10)
        df["intraday"] = df["date"].str.slice(11, 22)
        df["h"] = df["intraday"].str.slice(0, 2)
        df["m"] = df["intraday"].str.slice(3, 5)
        df["s"] = df["intraday"].str.slice(6, 8)

        df_result = pd.DataFrame()
        a_intraday = list(df["intraday"].unique())
        #1.part stats about mean and volatility
        for intraday in a_intraday:
            df_filter = df[df["intraday"] == intraday]
            mean = df_filter["pct_chg"].mean()
            pct_chg_pos=len(df_filter[df_filter["pct_chg"]>0])/len(df_filter)
            pct_chg_neg=len(df_filter[df_filter["pct_chg"]<0])/len(df_filter)
            std = df_filter["pct_chg"].std()
            sharp = mean / std
            df_result.at[intraday, "mean"] = mean
            df_result.at[intraday, "pos"] = pct_chg_pos
            df_result.at[intraday, "neg"] = pct_chg_neg
            df_result.at[intraday, "std"] = std
            df_result.at[intraday, "sharp"] = sharp
        df_result.to_csv(f"intraday{ts_code}.csv")


        #2.part:prediction. first 15 min predict today
        a_results=[]
        for intraday in a_intraday:
            df_day=get_asset(ts_code=ts_code,asset=asset)
            df_filter = df[df["intraday"] == intraday]
            df_filter["trade_date"]=df_filter["day"].apply(LB.trade_date_switcher)
            df_filter["trade_date"]=df_filter["trade_date"].astype(int)
            df_final=pd.merge(LB.ohlcpp(df=df_day), df_filter, on="trade_date", suffixes=["_d", "_15m"], sort=False)

            df_final["pct_chg_d"] = df_final["pct_chg_d"].shift(-1)
            df_final.to_csv(f"intraday_prediction_{ts_code}.csv")

            len_df=len(df_final)

            TT= len(df_final[(df_final["pct_chg_15m"]>0) & (df_final["pct_chg_d"]>0)])/len_df
            TF= len(df_final[(df_final["pct_chg_15m"]>0) & (df_final["pct_chg_d"]<0)])/len_df
            FT= len(df_final[(df_final["pct_chg_15m"]<0) & (df_final["pct_chg_d"]>0)])/len_df
            FF= len(df_final[(df_final["pct_chg_15m"]<0) & (df_final["pct_chg_d"]<0)])/len_df

            #rolling version
            rolling=5
            df_final[f"pct_chg_15m_r{rolling}"]=df_final[f"pct_chg_15m"].rolling(rolling).mean()
            pearson=df_final[f"pct_chg_15m_r{rolling}"].corr(df_final["pct_chg_d"])
            spearman=df_final[f"pct_chg_15m_r{rolling}"].corr(df_final["pct_chg_d"],method="spearman")

            s=pd.Series({"intraday":intraday,"TT":TT,"TF":TF,"FT":FT,"FF":FF,"pearson":pearson,"sparman":spearman})
            a_results.append(s)
        df_predict_result=pd.DataFrame(a_results)
        df_predict_result.to_csv(f"intraday_prediction_result_{ts_code}.csv")


def daily_stocks_abve():
    """this tells me how difficult my goal is to select the stocks > certain pct_chg every day
                get 1% everyday, 33% of stocks
                2% everyday 25% stocks
                3% everyda 19% stocks
                4% everyday 12% stocks
                5% everyday 7% stocks
                6% everyday 5%stocks
                7% everyday 3% stocks
                8% everday  2.5% Stocks
                9% everday  2% stocks
                10% everday, 1,5% Stocks  """

    df_asset = DB.preload("E", step=2)
    df_result = pd.DataFrame()
    for ts_code, df in df_asset.items():
        print("ts_code", ts_code)
        for pct in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
            df_copy=df[ (100*(df["pct_chg_open"]-1) >  pct) ]
            df_result.at[ts_code,f"pct_chg_open > {pct} pct"]=len(df_copy)/len(df)

            df_copy = df[(100 * (df["pct_chg_close"] - 1) > pct)]
            df_result.at[ts_code, f"pct_chg_close > {pct} pct"] = len(df_copy) / len(df)

            df_copy = df[(((df["close"]/df["open"]) - 1)*100 > pct)] #trade
            df_result.at[ts_code, f"trade > {pct} pct"] = len(df_copy) / len(df)

            df_copy = df[ ((df["co_pct_chg"]-1)*100 > pct)] #today open and yester day close
            df_result.at[ts_code, f"non trade > {pct} pct"] = len(df_copy) / len(df)
    df_result.to_csv("test.csv")


# WHO WAS GOOD DURING THAT TIME PERIOD
# ASSET INFORMATION
# measures the fundamentals aspect
"""does not work in general. past can not predict future here"""
def asset_fundamental(start_date, end_date, freq, assets=["E"]):
    asset = assets[0]
    ts_codes = DB.get_ts_code(a_asset=[asset])
    a_result_mean = []
    a_result_std = []

    ts_codes = ts_codes[::-1]
    small = ts_codes[(ts_codes["exchange"] == "创业板") | (ts_codes["exchange"] == "中小板")]
    big = ts_codes[(ts_codes["exchange"] == "主板")]

    print("small size", len(small))
    print("big size", len(big))

    ts_codes = ts_codes

    for ts_code in ts_codes.ts_code:
        print("start appending to asset_fundamental", ts_code)

        # get asset
        df_asset = DB.get_asset(ts_code, asset, freq)
        if df_asset.empty:
            continue
        df_asset = df_asset[df_asset["trade_date"].between(int(start_date), int(end_date))]

        # get all label
        fun_balancesheet_label_list = ["pe_ttm", "ps_ttm", "pb", "total_mv", "profit_dedt", "total_cur_assets", "total_nca", "total_assets", "total_cur_liab", "total_ncl", "total_liab"]
        fun_cashflow_label_list = ["n_cashflow_act", "n_cashflow_inv_act", "n_cash_flows_fnc_act"]
        fun_indicator_label_list = ["netprofit_yoy", "or_yoy", "grossprofit_margin", "netprofit_margin", "debt_to_assets", "turn_days"]
        fun_pledge_label_list = ["pledge_ratio"]
        fun_label_list = fun_balancesheet_label_list + fun_cashflow_label_list + fun_indicator_label_list + fun_pledge_label_list
        df_asset = df_asset[["ts_code", "period"] + fun_label_list]

        # calc reduced result
        ts_code = df_asset.at[0, "ts_code"]
        period = df_asset.at[len(df_asset) - 1, "period"]

        # calc result
        fun_result_mean_list = [df_asset[label].mean() for label in fun_label_list]
        fun_result_std_list = [df_asset[label].std() for label in fun_label_list]

        a_result_mean.append(list([asset, ts_code, period] + fun_result_mean_list))
        a_result_std.append(list([asset, ts_code, period] + fun_result_std_list))

    # create tab Asset View
    df_result_mean = pd.DataFrame(a_result_mean, columns=["asset"] + list(df_asset.columns))
    df_result_std = pd.DataFrame(a_result_std, columns=["asset"] + list(df_asset.columns))

    # create std rank
    # THE LESS STD THE BETTER
    df_result_mean["std_growth_rank"] = df_result_std["netprofit_yoy"] + df_result_std["or_yoy"]
    df_result_mean["std_margin_rank"] = df_result_std["grossprofit_margin"] + df_result_std["netprofit_margin"]
    df_result_mean["std_cashflow_op_rank"] = df_result_std["n_cashflow_act"]
    df_result_mean["std_cashflow_inv_rank"] = df_result_std["n_cashflow_inv_act"]
    df_result_mean["std_cur_asset_rank"] = df_result_std["total_cur_assets"]
    df_result_mean["std_cur_liab_rank"] = df_result_std["total_cur_liab"]
    df_result_mean["std_plus_rank"] = df_result_mean["std_growth_rank"] + df_result_mean["std_margin_rank"] + df_result_mean["std_cashflow_op_rank"] * 2 + df_result_mean["std_cashflow_inv_rank"] + df_result_mean["std_cur_asset_rank"] * 3

    df_result_mean["std_growth_rank"] = df_result_mean["std_growth_rank"].rank(ascending=False)
    df_result_mean["std_margin_rank"] = df_result_mean["std_margin_rank"].rank(ascending=False)
    df_result_mean["std_cashflow_op_rank"] = df_result_mean["std_cashflow_op_rank"].rank(ascending=False)
    df_result_mean["std_cashflow_inv_rank"] = df_result_mean["std_cashflow_inv_rank"].rank(ascending=False)
    df_result_mean["std_cur_asset_rank"] = df_result_mean["std_cur_asset_rank"].rank(ascending=False)
    df_result_mean["std_cur_liab_rank"] = df_result_mean["std_cur_liab_rank"].rank(ascending=False)
    df_result_mean["std_plus_rank"] = df_result_mean["std_plus_rank"].rank(ascending=False)

    # create mean rank

    # 7  asset rank
    # SMALLER BETTER, rank LOWER BETTER
    # the bigger the company, the harder to get good asset ratio
    df_result_mean["asset_score"] = (df_result_mean["debt_to_assets"] + df_result_mean["pledge_ratio"] * 3) * np.sqrt(df_result_mean["total_mv"])
    df_result_mean["asset_rank"] = df_result_mean["asset_score"].rank(ascending=True)

    # 0 mv score
    # Higher BETTER, the bigger the company the better return
    # implies that value stock are better than value stock
    df_result_mean["mv_score"] = df_result_mean["total_mv"]
    df_result_mean["mv_rank"] = df_result_mean["mv_score"].rank(ascending=False)

    # 6 cashflow rank
    # SMALLER BETTER, rank LOWER BETTER
    # cashflow the closer to profit the better
    df_result_mean["cashflow_o_rank"] = 1 - abs(df_result_mean["n_cashflow_act"] / df_result_mean["profit_dedt"])
    df_result_mean["cashflow_o_rank"] = df_result_mean["cashflow_o_rank"].rank(ascending=True)

    # higher the better
    df_result_mean["cashflow_netsum_rank"] = (df_result_mean["n_cashflow_act"] + df_result_mean["n_cashflow_inv_act"] + df_result_mean["n_cash_flows_fnc_act"]) / df_result_mean["total_mv"]
    df_result_mean["cashflow_netsum_rank"] = df_result_mean["cashflow_netsum_rank"].rank(ascending=False)

    df_result_mean["non_current_asset_ratio"] = df_result_mean["total_nca"] / df_result_mean["total_assets"]
    df_result_mean["non_current_liability_ratio"] = df_result_mean["total_ncl"] / df_result_mean["total_liab"]
    df_result_mean["current_liability_to_mv"] = df_result_mean["total_cur_assets"] / df_result_mean["total_mv"]

    # 8 other rank
    # SMALLER BETTER, rank LOWER BETTER
    df_result_mean["other_rank"] = df_result_mean["turn_days"]
    df_result_mean["other_rank"] = df_result_mean["other_rank"].rank(ascending=True)

    # 1 margin score
    # HIGHER BETTER, rank LOWER BETTER
    # the bigger and longer a company, the harder to get high margin
    df_result_mean["margin_score"] = (df_result_mean["grossprofit_margin"] * 0.5 + df_result_mean["netprofit_margin"] * 0.5) * (np.sqrt(df_result_mean["total_mv"])) * (df_result_mean["period"])
    df_result_mean["margin_rank"] = df_result_mean["margin_score"].rank(ascending=False)

    # 2 growth rank
    # the longer a firm exists, the bigger a company, the harder to keep growth rate
    # the higher the margin, the higher the growthrate, the faster it grow
    # HIGHER BETTER, rank LOWER BETTER
    df_result_mean["average_growth"] = df_result_mean["netprofit_yoy"] * 0.2 + df_result_mean["or_yoy"] * 0.8
    df_result_mean["period_growth_score"] = ((df_result_mean["average_growth"]) * (df_result_mean["margin_score"]))
    df_result_mean["period_growth_rank"] = df_result_mean["period_growth_score"].rank(ascending=False)

    # the bigger the better
    df_result_mean["test_score"] = df_result_mean["average_growth"] * (df_result_mean["grossprofit_margin"] * 0.5 + df_result_mean["netprofit_margin"] * 0.5) * np.sqrt(np.sqrt(np.sqrt(df_result_mean["total_mv"]))) * np.sqrt(df_result_mean["period"]) * (100 - df_result_mean["pledge_ratio"])
    df_result_mean["test_rank"] = df_result_mean["test_score"].rank(ascending=False)

    # 3 PEG
    # SMALLER BETTER, rank LOWER BETTER
    df_result_mean["peg_rank"] = df_result_mean["pe_ttm"] / df_result_mean["average_growth"]
    df_result_mean["peg_rank"] = df_result_mean["peg_rank"].rank(ascending=True)

    # 4 PSG
    # SMALLER BETTER, rank LOWER BETTER
    df_result_mean["psg_rank"] = df_result_mean["ps_ttm"] / df_result_mean["average_growth"]
    df_result_mean["psg_rank"] = df_result_mean["psg_rank"].rank(ascending=True)

    # 5 PBG
    # SMALLER BETTER, rank LOWER BETTER
    df_result_mean["pbg_rank"] = df_result_mean["pb"] / df_result_mean["average_growth"]
    df_result_mean["pbg_rank"] = df_result_mean["pbg_rank"].rank(ascending=True)

    # final rank
    df_result_mean["final_fundamental_rank"] = df_result_mean["margin_rank"] * 0.40 + \
                                               df_result_mean["period_growth_rank"] * 0.2 + \
                                               df_result_mean["peg_rank"] * 0.0 + \
                                               df_result_mean["psg_rank"] * 0.0 + \
                                               df_result_mean["pbg_rank"] * 0.0 + \
                                               df_result_mean["cashflow_o_rank"] * 0.0 + \
                                               df_result_mean["cashflow_netsum_rank"] * 0.1 + \
                                               df_result_mean["asset_rank"] * 0.05 + \
                                               df_result_mean["other_rank"] * 0.05 + \
                                               df_result_mean["std_plus_rank"] * 0.2
    df_result_mean["final_fundamental_rank"] = df_result_mean["final_fundamental_rank"].rank(ascending=True)

    # add static data and sort by final rank
    df_result_mean = DB.add_static_data(df_result_mean, assets=assets)
    df_result_mean = DB.add_asset_final_analysis_rank(df_result_mean, assets, freq, "bullishness")
    df_result_mean = DB.add_asset_final_analysis_rank(df_result_mean, assets, freq, "volatility")
    df_result_mean.sort_values(by=["final_fundamental_rank"], ascending=True, inplace=True)

    path = "Market/" + "CN" + "/Atest/" + "fundamental" + "/" + ''.join(assets) + "_" + freq + "_" + start_date + "_" + end_date + ".xlsx"
    DB.to_excel_with_static_data(df_result_mean, path=path, sort=["final_fundamental_rank", True], a_assets=assets)


# measures the volatility aspect
def asset_volatility(start_date, end_date, assets, freq):
    a_result = []
    for asset in assets:
        ts_codes = DB.get_ts_code(a_asset=[asset])
        for ts_code in ts_codes.ts_code:
            print("start appending to asset_volatility", ts_code)

            # get asset
            df_asset = DB.get_asset(ts_code, asset, freq)
            if df_asset.empty:
                continue
            df_asset = df_asset[df_asset["trade_date"].between(int(start_date), int(end_date))]

            # get all label
            close_std_label_list = [s for s in df_asset.columns if "close_std" in s]
            ivola_std_label_list = [s for s in df_asset.columns if "ivola_std" in s]
            turnover_rate_std_label_list = [s for s in df_asset.columns if "turnover_rate_std" in s]
            beta_list = [s for s in df_asset.columns if "beta" in s]

            std_label_list = close_std_label_list + ivola_std_label_list + turnover_rate_std_label_list + beta_list
            df_asset = df_asset[["ts_code", "period"] + std_label_list]

            # calc reduced result
            ts_code = df_asset.at[0, "ts_code"]
            period = df_asset.at[len(df_asset) - 1, "period"]

            # calc result
            std_result_list = [df_asset[label].mean() for label in std_label_list]

            df_asset_reduced = [asset, ts_code, period] + std_result_list
            a_result.append(list(df_asset_reduced))

    # create tab Asset View
    df_result = pd.DataFrame(a_result, columns=["asset"] + list(df_asset.columns))

    # ranking
    # price: the higher the volatility between close prices each D the better
    # interday: the higher interday volatility the better
    # volume: the lower tor the better
    # beta: the lower the beta the better

    # calculate score
    df_result["close_score"] = sum([df_result[label] for label in close_std_label_list]) / len(close_std_label_list)
    df_result["ivola_score"] = sum([df_result[label] for label in ivola_std_label_list]) / len(ivola_std_label_list)
    if (asset == "E"):
        df_result["turnover_rate_score"] = sum([df_result[label] for label in turnover_rate_std_label_list]) / len(turnover_rate_std_label_list)
    # df_result["beta_score"]=sum([df_result[label] for label in beta_list])

    # rank them
    df_result["close_rank"] = df_result["close_score"].rank(ascending=False)
    df_result["ivola_rank"] = df_result["ivola_score"].rank(ascending=False)
    if (asset == "E"):  # TODO add turnover_rate for I ,FD
        df_result["turnover_rate_rank"] = df_result["turnover_rate_score"].rank(ascending=True)
    # df_result["beta_rank"] = df_result["beta_score"].rank(ascending=True)

    # final rank
    if (asset == "E"):
        df_result["final_volatility_rank"] = df_result["close_rank"] + df_result["ivola_rank"] + df_result["turnover_rate_rank"]
    else:
        df_result["final_volatility_rank"] = df_result["close_rank"] + df_result["ivola_rank"]
    df_result["final_volatility_rank"] = df_result["final_volatility_rank"].rank(ascending=True)

    # add static data and sort by final rank
    df_result = DB.add_static_data(df_result, assets)
    df_result = DB.add_asset_final_analysis_rank(df_result, assets, freq, "bullishness")
    df_result.sort_values(by=["final_volatility_rank"], ascending=True, inplace=True)

    path = "Market/" + "CN" + "/Atest/" + "volatility" + "/" + ''.join(assets) + "_" + freq + "_" + start_date + "_" + end_date + ".xlsx"
    DB.to_excel_with_static_data(df_result, path=path, sort=["final_volatility_rank", True], a_assets=assets)


# measures the overall bullishness of an asset using GEOMEAN. replaces bullishness
def asset_bullishness(market="CN"):
    from scipy.stats import gmean
    df_ts_code = DB.get_ts_code(a_asset=["E","I","FD","F","G"],market=market)[::1]
    #df_ts_code.to_csv("check.csv",encoding="utf-8_sig")
    df_result = pd.DataFrame()

    df_sh_index = DB.get_asset(ts_code="000001.SH", asset="I",market="CN")
    df_sh_index["sh_close"] = df_sh_index["close"]
    df_sz_index = DB.get_asset(ts_code="399001.SZ", asset="I",market="CN")
    df_sz_index["sz_close"] = df_sz_index["close"]
    df_cy_index = DB.get_asset(ts_code="399006.SZ", asset="I",market="CN")
    df_cy_index["cy_close"] = df_cy_index["close"]
    for ts_code, asset in zip(df_ts_code.index, df_ts_code["asset"]):
        print("ts_code", ts_code, asset)
        df_asset = DB.get_asset(ts_code=ts_code, asset=asset,market=market)
        df_result.at[ts_code, "period"] = len(df_asset)
        try:
            df_asset = df_asset[(df_asset["period"] > 240)]
        except:
            continue

        if len(df_asset) > 100:
            # assed gained from lifetime. bigger better
            df_result.at[ts_code, "comp_gain"] = df_asset["close"].iat[len(df_asset) - 1] / df_asset["close"].iat[0]

            # period. the longer the better
            df_result.at[ts_code, "period"] = len(df_asset)

            # gain / period
            df_result.at[ts_code, "gain"] = df_result.at[ts_code, "comp_gain"] / df_result.at[ts_code, "period"]

            # Geomean.
            helper = 1 + (df_asset["pct_chg"] / 100)
            df_result.at[ts_code, "geomean"] = gmean(helper)

            # sharp/sortino ratio: Note my sharp ratio is not anuallized but period adjusted
            s=df_asset["pct_chg"]
            df_result.at[ts_code, "sharp"] = (s.mean()/s.std())*np.sqrt(len(s))
            #df_result.at[ts_code, "sortino"] = (s.mean()/s[s<0].std())*np.sqrt(len(s))

            # times above ma, bigger better
            # df_asset["abv_ma"] = 0
            # for freq in [240]:
            #     df_asset[f"highpass{freq}"] = Atest.highpass(df_asset["close"], freq)
            #     # df_asset[f"ma{freq}"] = df_asset["close"] - df_asset[f"highpass{freq}"]
            #     df_asset[f"ma{freq}"] = df_asset["close"].rolling(freq).mean()
            #     df_asset[f"abv_ma{freq}"] = (df_asset["close"] > df_asset[f"ma{freq}"]).astype(int)
            #     df_asset["abv_ma"] = df_asset["abv_ma"] + df_asset[f"abv_ma{freq}"]
            # df_result.at[ts_code, "abv_ma"] = df_asset["abv_ma"].mean()

            # trend swap. how long a trend average lasts
            # for freq in [240]:
            #     df_result.at[ts_code, f"abv_ma_days{freq}"] = LB.trend_swap(df_asset, f"abv_ma{freq}", 1)

            # volatility of the high pass, the smaller the better
            # highpass_mean = 0
            # for freq in [240]:
            #     highpass_mean = highpass_mean + df_asset[f"highpass{freq}"].mean()
            # df_result.at[ts_code, "highpass_mean"] = highpass_mean

            # volatility pct_ chg, less than better
            #df_result.at[ts_code, "rapid_down"] = len(df_asset[df_asset["pct_chg"] <= (-5)]) / len(df_asset)

            # beta, lower the better
            df_result.at[ts_code, "beta_sh"] = LB.calculate_beta(df_asset["close"], df_sh_index["sh_close"])
            df_result.at[ts_code, "beta_sz"] = LB.calculate_beta(df_asset["close"], df_sz_index["sz_close"])
            df_result.at[ts_code, "beta_cy"] = LB.calculate_beta(df_asset["close"], df_cy_index["cy_close"])

            # is_max. How long the current price is around the all time high. higher better
            # df_asset["expanding_max"] = df_asset["close"].expanding(240).max()
            # df_result.at[ts_code, "is_max"] = len(df_asset[(df_asset["close"] / df_asset["expanding_max"]).between(0.9, 1.1)]) / len(df_asset)

    #TODO update it to be exactly same as bullishness rank
    gmean_rank=df_result["geomean"].rank(ascending=False)
    sharp_rank=df_result["sharp"].rank(ascending=False)
    beta_sh_rank=df_result["beta_sh"].rank(ascending=True)
    beta_sz_rank=df_result["beta_sz"].rank(ascending=True)
    beta_cy_rank=df_result["beta_cy"].rank(ascending=True)
    df_result["final_rank"] = gmean_rank*0.45+\
                              sharp_rank*0.40+\
                              beta_sh_rank*0.05+\
                              beta_sz_rank*0.05+\
                              beta_cy_rank*0.05


    DB.to_excel_with_static_data(df_ts_code=df_result, sort=["final_rank", True], path=f"Market/{market}/Atest/bullishness/bullishness_{market}.xlsx", group_result=True, market=market)


def asset_candlestick_analysis_once(ts_code, pattern, func):
    df_asset = DB.get_asset(ts_code)
    rolling_freqs = [2, 5, 10, 20, 60, 240]
    # labels
    candle_1 = ["future_gain" + str(i) + "_1" for i in rolling_freqs] + ["future_gain" + str(i) + "_std_1" for i in rolling_freqs]
    candle_0 = ["future_gain" + str(i) + "_0" for i in rolling_freqs] + ["future_gain" + str(i) + "_std_0" for i in rolling_freqs]

    try:
        df_asset = df_asset[df_asset["period"] > 240]
        df_asset[pattern] = func(open=df_asset["open"], high=df_asset["high"], low=df_asset["low"], close=df_asset["close"])
    except:
        s_interim = pd.Series(index=["candle", "ts_code", "occurence_1", "occurence_0"] + candle_1 + candle_0)
        s_interim["ts_code"] = ts_code
        s_interim["candle"] = pattern
        return s_interim

    occurence_1 = len(df_asset[df_asset[pattern] == 100]) / len(df_asset)
    occurence_0 = len(df_asset[df_asset[pattern] == -100]) / len(df_asset)

    a_future_gain_1_mean = []
    a_future_gain_1_std = []
    a_future_gain_0_mean = []
    a_future_gain_0_std = []

    for freq in rolling_freqs:
        a_future_gain_1_mean.append(df_asset.loc[df_asset[pattern] == 100, "future_gain" + str(freq)].mean())
        a_future_gain_1_std.append(df_asset.loc[df_asset[pattern] == 100, "future_gain" + str(freq)].std())
        a_future_gain_0_mean.append(df_asset.loc[df_asset[pattern] == -100, "future_gain" + str(freq)].mean())
        a_future_gain_0_std.append(df_asset.loc[df_asset[pattern] == -100, "future_gain" + str(freq)].std())

    data = [pattern, ts_code, occurence_1, occurence_0] + a_future_gain_1_mean + a_future_gain_1_std + a_future_gain_0_mean + a_future_gain_0_std
    s_result = pd.Series(data=data, index=["candle", "ts_code", "occurence_1", "occurence_0"] + candle_1 + candle_0)
    return s_result


def asset_candlestick_analysis_multiple():
    d_pattern = LB.c_candle()
    df_all_ts_code = DB.get_ts_code(a_asset=["E"])

    for key, array in d_pattern.items():
        function = array[0]
        a_result = []
        for ts_code in df_all_ts_code.ts_code:
            print("start candlestick with", key, ts_code)
            a_result.append(asset_candlestick_analysis_once(ts_code=ts_code, pattern=key, func=function))

            df_result = pd.DataFrame(data=a_result)
            path = "Market/CN/Atest/candlestick/" + key + ".csv"
            df_result.to_csv(path, index=False)
            print("SAVED candlestick", key, ts_code)

    a_all_results = []
    for key, array in d_pattern.items():
        path = "Market/CN/Atest/candlestick/" + key + ".csv"
        df_pattern = pd.read_csv(path)
        df_pattern = df_pattern.mean()
        df_pattern["candle"] = key
        a_all_results.append(df_pattern)
    df_all_result = pd.DataFrame(data=a_all_results)
    path = "Market/CN/Atest/candlestick/summary.csv"
    df_all_result.to_csv(path, index=True)

def distribution(asset="I",column="close",bins=10):
    d_preload=DB.preload(asset=asset,step=5)

    for freq in [10,20,40,60,120,240,500]:
        a_path = LB.a_path(f"Market/CN/Atest/distribution/{asset}/{column}/{column}_freq{freq}_bin{bins}")
        df_result=pd.DataFrame()
        if not os.path.isfile(a_path[0]):
            for ts_code, df in d_preload.items():
                print(f"{asset}, freq{freq}, bins{bins}, {ts_code}, {column}")

                #normalize past n values to be between 0 and 1. 0 is lowest and 1 is highest.
                df["norm"] = df["close"].rolling(freq).apply(Alpha.normalize_apply, raw=False)

                #count cut as result
                df_result.at[ts_code,"len"]=len(df)
                for c1,c2 in LB.custom_pairwise_overlap(LB.drange(0,101,bins)):
                    df_result.at[ts_code,f"c{c1,c2}"]=len(df[df["norm"].between(c1,c2)])

            LB.to_csv_feather(df_result,a_path=a_path,skip_feather=True)

if __name__ == '__main__':
    # for column in ["ivola","close.pgain5","close.pgain10","close.pgain20","close.pgain60","close.pgain120","close.pgain240"]:
    #     atest_manu(fname="gq_rsi", a_abase=[column])
    #
    #

    pr = cProfile.Profile()
    pr.enable()

    # #prob_gain_asset()
    # df=DB.get_asset()
    # Plot.plot_distribution(df,abase="pct_chg")

    df_600519=DB.get_asset(ts_code="600276.SH")
    Plot.plot_distribution(df_600519,"close")

    # for asset in ["E","I","G"]:
    #     for column in ["pct_chg"]:
    #         distribution(asset=asset,column=column)
    #
    # distribution(asset="E", column="turnover_rate")

    #no_better_name()
    #atest_auto()
    #start_tester(asset="E",type="monthofyear")
    # df_sh=DB.get_asset("000001.SH",asset="I")
    # start_year_relation(df_sh,month=1)
    #pr.disable()
    #pr.print_stats(sort='file')



