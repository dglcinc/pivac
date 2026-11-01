import pandas as pd,numpy as np,sys,warnings
warnings.filterwarnings('ignore')
D=sys.argv[1]
df=pd.read_pickle(D+'/df.pkl'); df.index=pd.to_datetime(df.index,format='ISO8601',utc=True); df=df[df.wsup.notna()].resample('1min').mean().ffill(limit=3)
k=pd.read_csv(D+'/kids.csv',header=None,names=['t','kids']); k.index=pd.to_datetime(k.t,format='ISO8601',utc=True); df['kids']=k.kids.resample('1min').mean().reindex(df.index,method='nearest',limit=2)
df['mode']=np.where(df.st>0.9,'heat',np.where(df.st<-0.9,'cool','off')); df['run']=(df['mode']!=df['mode'].shift()).cumsum(); df['age']=df.groupby('run').cumcount()
df['dTa']=df.aret-df.asup; df['dTw']=df.wret-df.wsup; df['gap']=df.wsup-df.aret; df['eps']=df.dTa/df.gap
pd.set_option('display.width',170); pd.set_option('display.max_columns',30)
# 1 paired: 12-min before and after each Y2 rise, cold water only
ev=df.index[(df.y2>.5)&(df.y2.shift()<=.5)&(df['mode']=='cool')]
rows=[]
for t in ev:
    b=df[t-pd.Timedelta(minutes=12):t-pd.Timedelta(minutes=2)]; a=df[t+pd.Timedelta(minutes=5):t+pd.Timedelta(minutes=15)]
    if len(b)<8 or len(a)<8 or b.wsup.max()>60 or a.wsup.max()>60 or (b['mode']!='cool').any() or (a['mode']!='cool').any() or a.y2.min()<.9 or b.y2.max()>.1: continue
    rows.append(dict(t=t,wsB=b.wsup.mean(),wsA=a.wsup.mean(),dTaB=b.dTa.mean(),dTaA=a.dTa.mean(),dTwB=b.dTw.mean(),dTwA=a.dTw.mean(),epsB=-b.eps.mean(),epsA=-a.eps.mean(),kB=b.kids.mean(),kA=a.kids.mean(),rh=a.rh.mean()))
p=pd.DataFrame(rows); print('paired Y2 rises (cold water, same call):',len(p)); print(p.round(2).to_string(index=False))
if len(p):
    m=p.mean(numeric_only=True); print('mean Q ratio high/low (water):',round(m.dTwA/m.dTwB,2),' CFM ratio (q/dTa):',round((m.dTwA/m.dTaA)/(m.dTwB/m.dTaB),2))
# 2 cool calls with wrong-side water
c=df[df['mode']=='cool']; rows=[]
for r,g in c.groupby('run'):
    wrong=g[g.dTa<0]; hot=g[g.wsup>g.aret]
    rows.append(dict(t0=g.index[0].tz_convert('America/New_York').strftime('%m-%d %H:%M'),mins=len(g),wrongmin=len(hot),peakAsup=round(g.asup.max(),1),roomStart=g.room.iloc[0],roomEnd=g.room.iloc[-1],y2=round(g.y2.mean(),2),IN0=round(g.IN.iloc[0],1),heatBTU=round((480*5*(-g.dTw[g.wsup>g.aret]).clip(lower=0)/60).sum()),out=round(g.out.mean())))
w=pd.DataFrame(rows); print('\ncool calls'); print(w.to_string(index=False)); print('wrong-side minutes',w.wrongmin.sum(),'of',w.mins.sum(),'heat added BTU',w.heatBTU.sum())
# 3 room rate by stage when cold water
s=c[c.wsup<60]; s=s.assign(stage=np.where(s.y2>.9,'high','low'))
for st,g in s.groupby('stage'):
    print(st,'minutes',len(g),'room slope F/h',round(np.polyfit(np.arange(len(g)),g.room.values,1)[0]*60,3) if False else '', 'mean room-coolset',round((g.room-g.cset).mean(),2))
# rate per contiguous segment
seg=(s.stage!=s.stage.shift()).cumsum(); r=[]
for i,g in s.groupby(seg):
    if len(g)>=20 and (g.index[-1]-g.index[0]).total_seconds()/60<len(g)+5: r.append((g.stage.iloc[0],len(g),(g.room.iloc[-1]-g.room.iloc[0])/len(g)*60,g.out.mean()))
r=pd.DataFrame(r,columns=['stage','min','FperH','out']); print(r.groupby('stage').agg(n=('min','size'),mins=('min','sum'),rate=('FperH','median')).round(2))
# 4 heat steady versus kids calling, and water temp response
h=df[(df['mode']=='heat')&(df.age>=5)&(df.gap>15)&(df.hpcall>.9)]
h=h.assign(kidsCall=h.kids>.5); print('\nheat steady by kids call'); print(h.groupby('kidsCall').agg(n=('wsup','size'),wsup=('wsup','median'),dTw=('dTw','median'),dTa=('dTa','median'),eps=('eps','median'),asup=('asup','median')).round(2))
h=h.assign(wb=pd.cut(h.wsup,[90,105,110,113,116,125])); print(h.groupby('wb').agg(n=('wsup','size'),dTa=('dTa','median'),dTw=('dTw','median'),gap=('gap','median'),eps=('eps','median'),asup=('asup','median'),aret=('aret','median')).round(2))
c2=df[(df['mode']=='cool')&(df.age>=20)&(df.wsup<60)&(df.hpcall>.9)]; c2=c2.assign(kidsCall=c2.kids<-.5,stage=np.where(c2.y2>.9,'high','low'))
print('\ncool steady by stage/kids'); print(c2.groupby(['stage','kidsCall']).agg(n=('wsup','size'),wsup=('wsup','median'),dTw=('dTw','median'),dTa=('dTa','median'),eps=('eps','median'),rh=('rh','median'),aret=('aret','median')).round(2))
print('coil surface vs dew: rh, aret -> dew', )
a=c2.aret.median(); rh=c2.rh.median(); T=(a-32)/1.8; g=np.log(rh)+17.27*T/(237.3+T); print(round(a,1),rh,'dewF',round(237.3*g/(17.27-g)*1.8+32,1),'wsup',round(c2.wsup.median(),1))
# 5 what follows a call; st 0.5
df['st5']=df.st.round(2)==.5; seg=(df.st5!=df.st5.shift()).cumsum(); f=[]
for i,g in df[df.st5].groupby(seg):
    f.append((len(g),g.index[0].tz_convert('America/New_York').hour,df['mode'].shift(1).loc[g.index[0]],(g.hpcall>.5).mean()))
f=pd.DataFrame(f,columns=['n','hr','before','hp']); print('\nst=.5 runs',len(f),'median',f.n.median(),'before',f.before.value_counts().to_dict(),'hours',f.hr.value_counts().sort_index().to_dict())
# 6 calls per day, last 12 min, mode
print('\nheat calls per day',round((df[df['mode']=='heat'].groupby('run').size().count())/((df.index[-1]-df.index[0]).days),1),'cool',round((df[df['mode']=='cool'].groupby('run').size().count())/((df.index[-1]-df.index[0]).days),1))
hr=df[df.hpheat>.9].groupby(df[df.hpheat>.9].index.tz_convert('America/New_York').hour).st.apply(lambda x:(x>.9).mean()).round(2); print('heat duty by hour',hr.to_dict())
# 7 UA fit
for name,cfm,gpm,e,k_ in (('heat low',300,5,.925,480),('cool low',380,5,.858,490),('cool high',600,5,.745,490)):
    Ca=1.08*cfm;Cw=k_*gpm;Cr=Ca/Cw
    # crossflow Cmin mixed approx: counterflow form
    from math import log
    NTU=[n/100 for n in range(10,800) if abs(((1-np.exp(-n/100*(1-Cr)))/(1-Cr*np.exp(-n/100*(1-Cr))))-e)<.003]
    print(name,'Cr',round(Cr,2),'NTU',NTU[0] if NTU else None,'UA',round(NTU[0]*Ca) if NTU else None)
