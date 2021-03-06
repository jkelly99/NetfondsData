# -*- coding: utf-8 -*-
import pandas as pd
import os
os.chdir('D:\\Google Drive\\Python\\FinDataDownload')
import multi_intraday_pull2 as mul
import Netfonds_Ticker_List as NTL   
import multiprocessing
import sys
import time
import StringIO

def setup_parallel(toget=['SPX','ETF'], mktdata='combined', n_process=3, 
                    baseDir = 'D:\\Financial Data\\Netfonds\\DailyTickDataPull', supress='yes'):
    
    #some args for the write file
    directory = baseDir
    date = pd.datetime.strptime(pd.datetime.now().strftime('%Y%m%d'),'%Y%m%d')  - pd.offsets.BDay(1)
    datestr = date.strftime('%Y%m%d')
    
    #get list of tickers
    tickers = NTL.get_netfonds_tickers(toget) #get list of tickers from files or internet
    
    #break up problem into thirds, or number of processes
    length = len(tickers)
    index=[]
    df_list=[]
    for i in range(n_process):
        index.append(range(i,length, n_process)) 
        df = tickers.loc[index[i]] 
        df.index=range(len(df))
        df_list.append(df)
    
    queue = multiprocessing.Queue()
    start = time.time()
    
    #read in latest_dates
    if not(os.path.isfile(directory+'\\latest_dates\\latest_dates.csv')):
        print 'No latest_date.csv file found'
        print 'program terminated'
        return        
        
    latest_dates_df = pd.read_csv(directory+'\\latest_dates\\latest_dates.csv', index_col = 0, header=0)
    latest_dates_df['latest_date'] = pd.to_datetime(latest_dates_df['latest_date'])  
    print 'Read Latest_dates using pd.read_csv'    
    
    #start the writing file process
    w = multiprocessing.Process(target=write_latest_dates, args=(queue,latest_dates_df, directory, date, datestr, length))    
    w.start()  
    
    #start the pull data processes
    jobs=[]
    for tickers in df_list:
        p = multiprocessing.Process(target=pull_tickdata_parallel, args=(queue, tickers,latest_dates_df, 'combined', length, start, directory, supress))
        jobs.append(p)
        p.start()
    
    for j in jobs:
        j.join()
        
    print 'Joined other threads'
    queue.put('DONE')  #end the while loop in process 'w'
    w.join() #wait for join to happen
    print 'Joined the write thread'
    
    
    
def write_latest_dates(queue,latest_dates_df, directory, date, datestr, length):
    print 'Entered write_lates_dates function'    
          
    log_file_output = open(directory+'\\logfiles\\logfile'+ datestr +'.txt','w')
    log_file_output2 = open(directory+'\\logfiles\\logfile.txt','a')
    i=0
    while True:
        ret = queue.get()         

        if (type(ret) == tuple):
            i = i+1
            msg, tempstr = ret
            if msg.keys()[0] in latest_dates_df.index:
                latest_dates_df.ix[msg.keys()[0]]=msg.values()[0]
            else:
                latest_dates_df.set_value(index=msg.keys()[0], col='latest_date',value=msg.values()[0])
                print 'Added %s to latest_date file' %msg.keys()[0]
                
            latest_dates_df.to_csv(directory+'\\latest_dates\\latest_dates.csv')         
            latest_dates_df.to_csv(directory+'\\latest_dates\\latest_dates%s.csv'%datestr) 
            ind = tempstr.index('Iter=')
            tempstr=tempstr.replace(tempstr[ind:(ind+10)], 'Iter=%5d of %5d'%(i,length) )            
            print tempstr
            sys.stdout.flush()
            
            log_file_output.write(tempstr + '\n')
            log_file_output2.write(tempstr + '\n')            
            del msg[msg.keys()[0]]
            
        elif (ret == 'DONE'): #'DONE' is passed to queue from the main function when the data pull processed join()
            break
    
        else:
            print 'Error: ret from queue not as ecpected'
            print ret
            break
    
    log_file_output.close()
    log_file_output2.close()  
    return 
    


def pull_tickdata_parallel(queue, tickers, latest_date, mktdata='combined',nTot=0,sTime=0, directory='', supress='yes'):
    """
    pulls intraday data, for multiple days, for specified tickers, from netfonds.com
    """ 
    mktdata=mktdata.lower() #convert to lower case
    
    #get todays date, but with time of day set to zero    
    date = pd.datetime.strptime(pd.datetime.now().strftime('%Y%m%d'),'%Y%m%d')  - pd.offsets.BDay(1)
    ndays = 18

    pName = multiprocessing.current_process().name    
    
    for i in tickers.index:
        name = tickers['ticker'][i]
        folder=tickers['folder'][i]
        #get start date
        if (name in latest_date.index):
            start_date = (latest_date.latest_date.ix[name] + pd.offsets.BDay(1))
        else:
            start_date = date - pd.offsets.BDay(ndays)
            
        if start_date>date:
            print pName+ ':Iteration='+str(i) +' : Already collected data for '+name
            sys.stdout.flush()            
            continue
        
        #pull intraday data from the web for the current stock or index
        #positions, trades, combined 
        if supress=='yes': #suppresses the print statements in multi_intraday_pull2()
            sys.stdout = StringIO.StringIO()
            
        data = mul.multi_intraday_pull2(name, pd.datetime.date(start_date), date.date(), 30,mktdata, folder, directory)
        print pName+ ": %-3s daily files written: "%data +name +': Iter=%5d'%i +' completed: Starts:ends='+ start_date.strftime('%Y-%m-%d')+':'+date.strftime('%Y-%m-%d')
        
        if supress=='yes':
            sys.stdout = sys.__stdout__          
          
        tempstr = '%-12s: %-10s: Iter=%5d'%(pName,name,i)+ ', %-3s'%data +'dates complete in %5.2f min'%((time.time()-sTime)/60)        
        to_pass = ({name:date}, tempstr)
        queue.put(to_pass)  
        sys.stdout.flush()
    
    return 
    
if __name__=='__main__':    
    exper = ''  #\\temp  
    directory = 'D:\\Financial Data\\Netfonds%s\\DailyTickDataPull'%exper  
    ls=setup_parallel(toget=['ETF'], mktdata='combined', n_process=6,baseDir = directory)
    print 'hey'