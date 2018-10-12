# -*- coding: utf-8 -*-
"""
Created on Thu Jul 26 14:46:22 2018

@author: fenggjua
"""

import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date,timedelta
import time
import os

def get_rised_stock(df,percent):
    return df[df.changepercent>=percent]

def get_stocks_by_date(code,sDate,eDate):
    return ts.get_k_data(code,start=sDate,end=eDate)

def get_volume_pic_by_month(sDate,eDate):
    csv_name = 'datas/'+sDate+"~"+eDate+"_history.csv"
    if(os.path.exists(csv_name) == False):
        get_data_frame_of_shsz_to_csv(sDate,eDate)
        # 按月查看成交量的变化
    df =  pd.read_csv(csv_name)
    list1 = []
    for i in range(len(df)):
        dateStr=df['date'][i][:-3]
        list1.append(dateStr)
    df['month'] = list1
    
    se_month_sum = df.groupby('month').sum().volume
    x = se_month_sum.index
    y = se_month_sum.values
    plt.subplot(3,1,1)
    plt.title('按月成交量')
    plt.plot(x,y,'r-') 
    plt.xlabel('month')
    plt.ylabel('volume')
    
    df_sh = df.loc[df['code']=='sh']
    se_sh_month_mean_close = df_sh.groupby('month').mean().close
    plt.subplot(3,1,2)
    plt.title('上证收盘点平均值')
    plt.plot(se_sh_month_mean_close.index,se_sh_month_mean_close.values,'b-')
    
    df_sz = df.loc[df['code']=='sz']
    se_sz_month_mean_close = df_sz.groupby('month').mean().close
    plt.subplot(3,1,3)
    plt.title('深证收盘点平均值')
    plt.plot(se_sz_month_mean_close.index,se_sz_month_mean_close.values,'g-')
    
def get_data_frame_of_shsz_to_csv(sDate,eDate):
    df_history = get_stocks_by_date('sh',sDate,eDate)
    df_sz_history = get_stocks_by_date('sz',sDate,eDate)
    
    df = pd.concat([df_history,df_sz_history])
    df.to_csv('datas/'+sDate+"~"+eDate+"_history.csv",na_rep = 'NA',index=0,encoding='UTF-8')  
    
def get_top_amount_stocks_from_csv(csv_name,count):
    df_all_today =  pd.read_csv(csv_name,converters={'code':str})
    df_all_today_sorted = df_all_today.sort_values(by='amount',ascending=False)
    return df_all_today_sorted[:count]
   
#date.weekday()：返回weekday，如果是星期一，返回0；如果是星期2，返回1，以此类推；
#data.isoweekday()：返回weekday，如果是星期一，返回1；如果是星期2，返回2，以此类推；
def getLastWorkDay(day=date.today()):
    now=day
    if now.isoweekday()==1:
      dayStep=3
    else:
      dayStep=1
    lastWorkDay = now - timedelta(days=dayStep)
    return lastWorkDay

def generate_daily_stock_report(isRealtimeReport=True):
    old_width = pd.get_option('display.max_colwidth')
    pd.set_option('display.max_colwidth', -1)
    
    today = time.strftime("%Y-%m-%d")
    today_csv_name = "datas/"+today+"_detail.csv"
    
    last_workday = getLastWorkDay()
    last_workday_str = last_workday.strftime("%Y-%m-%d")
    
    # 存取行情数据
    if(isRealtimeReport):
        today = time.strftime("%Y-%m-%d_%H-%M-%S")
        today_csv_name = "datas/"+today+"_detail.csv"
        
    if(os.path.exists(today_csv_name) == False):
        df_all_today = ts.get_today_all()
        df_all_today_sorted = df_all_today.sort_values(by='amount',ascending=False)
        df_all_today_sorted.to_csv(today_csv_name,na_rep = 'NA',encoding='UTF-8',index=0)
        # 存取当天最大成交量top 50
        df_top_amount = df_all_today_sorted[:50]
        df_top_amount.columns=['代码','名称','涨跌幅','现价','开盘价','最高价','最低价','昨日收盘价','成交量','换手率','成交额','市盈率','市净率','总市值','流通市值']
        df_top_amount.to_html('html_reports/'+today+'_top_amount_stocks.html',escape=False,sparsify=True,index=False)
    
    df_all_today = pd.read_csv(today_csv_name,converters={'code':str})
    zt_lastworkday_file_name = "datas/"+last_workday_str+"_rised.csv"
    df_zt_lastworkday = pd.DataFrame(columns=['code','name','trade','rised_time','industry'])
    if(os.path.exists(zt_lastworkday_file_name)):
        df_zt_lastworkday = pd.read_csv(zt_lastworkday_file_name,converters={'code':str})
    
    # 拿取所有代码所属行业
    industries_file = 'datas/industries.csv'
    if(os.path.exists(industries_file) == False):
        df_stock = ts.get_stock_basics()
        df_stock.to_csv(industries_file,na_rep = 'NA',encoding='UTF-8')
    allIndustry = pd.read_csv(industries_file,converters={'code':str})
    #存取当天涨停的股票
    df_rised = pd.DataFrame(columns=['code','name','trade','rised_time','industry'])
    zt_count = 0
    fb_count = 0
    for i in range(len(df_all_today)):
        name = df_all_today['name'].values[i]
        # B股不用计算
        if name.endswith('B'):
            continue
        trade = df_all_today['trade'].values[i]
        settlement = df_all_today['settlement'].values[i]
        high = df_all_today['high'].values[i]
        code = df_all_today['code'].values[i]
        
        # 是否涨停过
        if is_ZDB(high,settlement):
            zt_count += 1
            # 涨停价格 == 现价，则说明封板（收盘时还涨停）
            if high == trade:
                fb_count += 1
                # 计算涨停时间
                #查看涨停的股票的当天分笔交易信息
                first_deal_time = ''
                if(isRealtimeReport == False):
                    df_rised_list_details = ts.get_today_ticks(code,pause=1) 
                    df_rised_price_list_details = df_rised_list_details.loc[df_rised_list_details['price'] == trade]
                    if(len(df_rised_price_list_details)>0 ):
                        first_deal_time = df_rised_price_list_details['time'].values.min()
                    print(code+":"+first_deal_time)
                # 拿取所属行业
                industry = ''
                if(len(allIndustry[allIndustry.code==code])>0):
                    industry = allIndustry[allIndustry.code==code].industry.values[0]
                df_rised.loc[len(df_rised)]=[code,df_all_today['name'].values[i],df_all_today['trade'].values[i],first_deal_time,industry]
    
    daily_report_df = df_rised.sort_values(by='industry')
    daily_report_df.to_csv('datas/'+today+"_rised.csv",na_rep = 'NA',encoding='UTF-8',index=0)
    daily_report_df.columns=['代码','名称','价格','涨停时间','所属行业']
    daily_report_df.to_html('html_reports/'+today+'_top_rised_stocks.html',escape=False,index=False,sparsify=True)
    rate = get_real_time_rate(fb_count,zt_count)
    # 计算昨日涨停高开率
    higher_rate = get_open_higher_rate_in_rised(df_zt_lastworkday,df_all_today)
    
    generate_html_daily_report(today,rate,higher_rate,isRealtimeReport)
    pd.set_option('display.max_colwidth', old_width)
    
def get_real_time_rate(rised_count,touch_count):
    """
    得到封板率（封死涨停-触摸涨停）
    """
    if(touch_count>0):
        return rised_count/touch_count
    else:
        return 0

def get_open_higher_rate_in_rised(df_rised_yesterday,df_all_today):
    """
    昨日涨停高开率
    """
    if(len(df_rised_yesterday)>0):
        count = 0
        for i in range(len(df_rised_yesterday)):
            code = df_rised_yesterday['code'].values[i]
            if(len(df_all_today[df_all_today.code == code].open.values)==0):
                continue  
            open_today = df_all_today[df_all_today.code == code].open.values[0]
            close_yesterday = df_rised_yesterday['trade'].values[i]
            if(open_today > close_yesterday):
                count += 1
        return count/len(df_rised_yesterday)  
    else:
        return 0

def generate_html_daily_report(today,rate,higher_rate,isRealtimeReport=True):
    HTML="""
    <!DOCTYPE html>
    <html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <title>Daily Report({today})</title>
    <meta name="keywords" content="daily report" />
    <meta name="description" content="stock daily report" />
    
    <script language="JavaScript" type="text/javascript">
    </script>
    
    <style type="text/css">
    </style>
    
    </head>
    
    <body>
        <h1>{today}行情</h1>
        <h4>{current}实时封板率为：{rate}</h4>
        <h4>昨日涨停高开率为：{higher_rate}</h4>
        <h2>{current}涨停股票</h2>
        <div class="top_rised_stocks">
           {top_rised_stocks}
        </div>
        <hr />
        <h2>成交额(top 50)</h2>
        <div class='top_amount_stocks'>
            {top_amount_stocks}
        </div>
    
    </body>
    </html>
    """
    HTML = HTML.replace('{today}',today)
    HTML = HTML.replace('{rate}',"%.2f%%" % (rate * 100))
    HTML = HTML.replace('{higher_rate}',"%.2f%%" % (higher_rate * 100))
    if(isRealtimeReport):
        HTML = HTML.replace('{current}','现在')
    else:
        HTML = HTML.replace('{current}','收盘时')
    top_r = get_html_content('html_reports/'+today+'_top_rised_stocks.html')
    top_v = get_html_content('html_reports/'+today+'_top_amount_stocks.html')
    HTML = HTML.replace('{top_rised_stocks}',top_r)
    HTML = HTML.replace('{top_amount_stocks}',top_v)
    fh = open('html_reports/daily_report_'+today+'.html', 'w',encoding='utf8')
    fh.write(HTML)
    fh.close()

def is_ZDB(today_close,yesterday_close):
    """
    是否是涨停价格
    """
    if yesterday_close==0:
        return False
    rise_rate = (today_close+0.01)/yesterday_close
    if(rise_rate > 1.1):
        return True
    else:
        return False
    
def get_html_content(fileName):
    tr = open(fileName)
    content = tr.read()
    return content
    
if __name__ == "__main__":
    """
       
    # 按月查看深沪的成交量，画出曲线
    sDate = '2007-06-01'
    eDate = '2018-07-31'
    get_volume_pic_by_month(sDate,eDate)
      
    df_stock = ts.get_stock_basics()
    df_stock.to_csv('datas/industries.csv',na_rep = 'NA',encoding='UTF-8')
"""
    # 生成日报
    generate_daily_stock_report(False)