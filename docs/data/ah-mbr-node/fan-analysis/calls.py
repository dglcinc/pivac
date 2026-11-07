# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
import pandas as pd,numpy as np,sys
df=pd.read_pickle(sys.argv[1]+'/df.pkl'); df.index=pd.to_datetime(df.index,format='ISO8601',utc=True); df=df[df.wsup.notna()].resample('1min').mean().ffill(limit=3)
df['mode']=np.where(df.st>0.9,'heat',np.where(df.st<-0.9,'cool','off'))
# calls: runs of the thermostat in heat or cool
df['run']=(df['mode']!=df['mode'].shift()).cumsum()
df['age']=df.groupby('run').cumcount()
df['dTa']=df.aret-df.asup; df['dTw']=df.wret-df.wsup; df['gap']=df.wsup-df.aret; df['eps']=df.dTa/df.gap
df['loopgap']=df.wsup-df.lsup
pd.set_option('display.width',170); pd.set_option('display.max_columns',30)
print('minutes by mode',df['mode'].value_counts().to_dict(),'days',round(len(df)/1440,1))
runs=df[df['mode']!='off'].groupby('run').agg(mode=('mode','first'),t0=('wsup',lambda s:s.index[0]),n=('wsup','size'),y2=('y2','mean'),out=('out','mean'),hpcall=('hpcall','mean'),wmax=('wsup','max'),wmin=('wsup','min'))
print(runs.groupby('mode').agg(calls=('n','size'),med=('n','median'),p90=('n',lambda s:s.quantile(.9)),mins=('n','sum'),y2frac=('y2','mean'),hpcall=('hpcall','mean')).round(2))
print('calls with any y2:',runs[runs.y2>0].groupby('mode').size().to_dict())
# water actually useful
h=df[(df['mode']=='heat')]; c=df[df['mode']=='cool']
print('\nHEAT: wsup quantiles by age'); print(h.groupby(pd.cut(h.age,[-1,1,3,5,8,12,20,40,400])).agg(n=('wsup','size'),wsup=('wsup','median'),wret=('wret','median'),asup=('asup','median'),aret=('aret','median'),lsup=('lsup','median'),IN=('IN','median'),hpcall=('hpcall','mean')).round(1))
print('\nCOOL: by age'); print(c.groupby(pd.cut(c.age,[-1,1,3,5,8,12,20,40,400])).agg(n=('wsup','size'),wsup=('wsup','median'),wret=('wret','median'),asup=('asup','median'),aret=('aret','median'),lsup=('lsup','median'),IN=('IN','median'),hpcall=('hpcall','mean')).round(1))
for m,sel,minw in (('heat',(df['mode']=='heat')&(df.hpheat>.9)&(df.hpcall>.9)&(df.gap>15),0),('cool',(df['mode']=='cool')&(df.hpcool>.9)&(df.hpcall>.9)&(df.gap<-8),0)):
    s=df[sel&(df.age>=8)].copy(); s['stage']=np.where(s.y2>.9,'high',np.where(s.y2<.1,'low','mix'))
    print('\n',m,'steady, age>=8');
    print(s.groupby('stage').agg(n=('wsup','size'),wsup=('wsup','median'),wret=('wret','median'),asup=('asup','median'),aret=('aret','median'),dTa=('dTa','median'),dTw=('dTw','median'),gap=('gap','median'),eps=('eps','median'),out=('out','median'),rh=('rh','median')).round(3))
    for gpm in (3.9,4.5):
        k=480 if m=='heat' else 490
        s2=s[s.stage!='mix'];q=k*gpm*s2.dTw.abs(); 
        print(' gpm',gpm,'water MBH by stage',(q/1000).groupby(s2.stage).median().round(1).to_dict(),'implied CFM (sensible=water)',(q/(1.08*s2.dTa.abs())).groupby(s2.stage).median().round(0).to_dict())
# fan only
f=df[(df.st.round(2)==.5)]
print('\nst=0.5 (fan only?) minutes',len(f),f[['aret','asup','wsup','wret','hpcall','y2']].median().round(1).to_dict())
print(df[df.room>78][['room','aret','asup','out','st']].resample('1h').mean().dropna().head(8).round(1))
print('\nduty by outdoor bin, heat call share of minutes, HP in heat')
b=df[df.hpheat>.9].copy(); b['bin']=pd.cut(b.out,[30,40,45,50,55,60,70]); print(b.groupby('bin').agg(mins=('out','size'),heat=('st',lambda x:(x>.9).mean()),room=('room','mean'),y2=('y2','mean'),IN=('IN','mean')).round(3))
b=df[df.hpcool>.9].copy(); b['bin']=pd.cut(b.out,[30,50,55,60,65,70]); print(b.groupby('bin').agg(mins=('out','size'),cool=('st',lambda x:(x<-.9).mean()),room=('room','mean'),y2=('y2','mean'),IN=('IN','mean'),rh=('rh','mean')).round(3))
