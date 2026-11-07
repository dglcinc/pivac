# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
import pandas as pd,numpy as np,sys,warnings
warnings.filterwarnings('ignore')
df=pd.read_pickle(sys.argv[1]+'/u.pkl')
c=df[(df['mode']=='cool')&(df.ws<df.room-8)]
for lo in (2,3,4,5,6):
    s=c[c.age>=lo]; print('age>=',lo,'n',len(s),'ws',round(s.ws.median(),2),'wr',round(s.wr.median(),2),'dTw',round(s.dTw.median(),2),'p10-90',round(s.dTw.quantile(.1),2),round(s.dTw.quantile(.9),2),'room',round(s.room.median(),1),'rh',round(s.rh.median(),3),'rpm',round(s.rpm.median()))
s=c[c.age>=3]; gap=(s.room-s.ws).median(); dtw=s.dTw.median()
print('gap',round(gap,1))
for gpm in (5,6,6.5,7.4,7.8):
    q=490*gpm*dtw; print('GPM',gpm,'MBH',round(q/1000,1),'air dT at 300',round(q/(1.08*300),1),'eps',round(q/(1.08*300*gap),2))
print('max possible at eps=1, 300 CFM: MBH',round(1.08*300*gap/1000,1))
T=(s.room.median()-32)/1.8; rh=s.rh.median(); g=np.log(rh)+17.27*T/(237.3+T); print('dew F',round(237.3*g/(17.27-g)*1.8+32,1))
print('rpm/cfm',round((s.rpm/s.cfm).median(),3),'500 CFM by fan law',round((s.rpm/s.cfm).median()*500),'CFM at 1800',round(1800/(s.rpm/s.cfm).median()))
print('room quantiles by hour EDT',df.groupby(df.index.tz_convert('America/New_York').hour).room.mean().round(1).to_dict())
print('room min',df.room.min(),'hours at 72.x',round((df.room<73).mean()*len(df)/60,1),'heat set',round((df.hset.median()+459.67)*5/9,1),'cool set',round((df.cset.median()+459.67)*5/9,1))
print('cool mins by day',df[df['mode']=='cool'].groupby(df[df['mode']=='cool'].index.tz_convert('America/New_York').date).size().to_dict())
