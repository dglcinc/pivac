# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
import pandas as pd,numpy as np,sys,warnings
warnings.filterwarnings('ignore')
D=sys.argv[1]
df=pd.read_pickle(D+'/df.pkl'); df.index=pd.to_datetime(df.index,format='ISO8601',utc=True); df=df[df.wsup.notna()].resample('1min').mean().ffill(limit=3)
df['mode']=np.where(df.st>0.9,'heat',np.where(df.st<-0.9,'cool','off')); df['run']=(df['mode']!=df['mode'].shift()).cumsum(); df['age']=df.groupby('run').cumcount()
ny=lambda t:t.tz_convert('America/New_York').strftime('%m-%d %H:%M')
print('long cool calls: y2 start, water turns cold, room during')
for r,g in df[df['mode']=='cool'].groupby('run'):
    if len(g)<30: continue
    y=g[g.y2>.5]; cold=g[g.wsup<g.aret]
    pre=df[g.index[0]-pd.Timedelta(minutes=30):g.index[0]]
    print(ny(g.index[0]),'len',len(g),'y2 first age',(y.age.iloc[0] if len(y) else None),'y2 mins',len(y),'cold at age',(cold.age.iloc[0] if len(cold) else None),'room pre/max/end',round(pre.room.max(),1),round(g.room.max(),1),round(g.room.iloc[-1],1),'humid',round(g.rh.mean(),2),'hpcool before',round(pre.hpcool.mean(),2))
ch=df.hpcool.round(); rise=df.index[(ch>.5)&(ch.shift()<.5)]; fall=df.index[(ch<.5)&(ch.shift()>.5)]
print('\nchangeovers to cool',len(rise),'to heat',len(fall),'days',round((df.index[-1]-df.index[0]).total_seconds()/86400,1))
n=0
for t in rise:
    near=df[t-pd.Timedelta(minutes=6):t+pd.Timedelta(minutes=6)]
    m=(near.st<-.9).any(); n+=m; print(' to cool',ny(t),'MBR cool within 6 min:',bool(m))
print('MBR coincides with',n,'of',len(rise))
# model
def eps(NTU,Cr): 
    return (1-np.exp(-NTU*(1-Cr)))/(1-Cr*np.exp(-NTU*(1-Cr)))
def ntu(e,Cr):
    x=np.linspace(.05,8,8000); return x[np.argmin(abs(eps(x,Cr)-e))]
g=4.9; Cw=480*g
base=1.08*300; e0=.925; UA0=ntu(e0,base/Cw)*base
print('\nHEAT model UA300',round(UA0),'gap 40.4 room 73.3')
for n_ in (.35,.5):
  for cfm in (300,350,400,450,500):
    Ca=1.08*cfm; UA=UA0*(cfm/300)**n_; e=eps(UA/Ca,Ca/Cw); Q=e*Ca*40.4
    gap_same=12150/(e*Ca)
    print(f'n={n_} {cfm} CFM eps {e:.3f} Q@113.6F {Q/1000:.1f} MBH supply {73.3+Q/Ca:.0f}F dTw {Q/Cw:.1f}  for same 12.15MBH: water {73.3+gap_same:.0f}F supply {73.3+12150/Ca:.0f}F return {73.3+gap_same-12150/Cw:.0f}F')
# cooling model with offsets corrected
for cfm,e,dtw,dta in ((300,.858,2.73,19.27),(500,.745,4.0,16.77)):
    print('cool',cfm,'GPM from balance',round(1.08*cfm*dta/(490*dtw),2))
print('heat 300 GPM from balance',round(1.08*300*37.47/(480*5.0),2))
