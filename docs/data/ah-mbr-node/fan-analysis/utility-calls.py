# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
import pandas as pd,numpy as np,sys,warnings
warnings.filterwarnings('ignore')
D=sys.argv[1]; P='environment.inside.hvac.ah.utility.'; T='environment.inside.thermostat.'
n={P+'fan.airflow':'cfm',P+'fan.rpm':'rpm',P+'call.g':'g',P+'call.y1':'y1',P+'call.y2':'y2',P+'call.w1':'w1',P+'call.w2':'w2',P+'call.e':'e','environment.inside.hvac.LOOPB_SUP.temperature':'ws','environment.inside.hvac.LOOPB_RET.temperature':'wr','environment.inside.hvac.IN.temperature':'IN',T+'DSTRS_FAM_ROOM.statenum':'st',T+'DSTRS_FAM_ROOM.temperature':'room',T+'DSTRS_FAM_ROOM.humidity':'rh',T+'DSTRS_FAM_ROOM.heatset':'hset',T+'DSTRS_FAM_ROOM.coolset':'cset',T+'KITCHEN.statenum':'kit',T+'GREAT_ROOM.statenum':'grt','environment.outside.thermostat.temperature':'out','electrical.ac.switch.utility.HPHEAT.statenum':'hpheat','electrical.ac.switch.utility.HPCOOL.statenum':'hpcool','electrical.ac.switch.utility.HPCALL.statenum':'hpcall'}
fr={}
for m,c in n.items():
    d=pd.read_csv(f'{D}/{m}.csv',header=None,names=['t',c]); d.index=pd.to_datetime(d.t,format='ISO8601',utc=True); fr[c]=d[c].resample('1min').mean()
df=pd.DataFrame(fr).ffill(limit=3)
for c in ['ws','wr','IN','room','hset','cset','out']:
    df[c]=df[c]*9/5-459.67
df=df[df.cfm.notna()|df.y1.notna()]
pd.set_option('display.width',170); pd.set_option('display.max_columns',30)
print(df.index.min(),df.index.max(),round(len(df)/1440,1),'days; rows with cfm',df.cfm.notna().sum())
print(df[['cfm','rpm','room','rh','hset','cset','out']].describe().T[['count','mean','min','max']].round(1))
def stage(r):
    for k in ('e','w2','w1','y2','y1','g'):
        if r[k]>.9: return k
    return 'off'
df['stage']=df[['e','w2','w1','y2','y1','g']].apply(stage,axis=1,raw=False)
print(df.groupby('stage').agg(mins=('cfm','size'),cfm=('cfm','median'),cmin=('cfm',lambda s:s.quantile(.05)),cmax=('cfm',lambda s:s.quantile(.95)),rpm=('rpm','median'),rmin=('rpm',lambda s:s.quantile(.05)),rmax=('rpm',lambda s:s.quantile(.95))).round(0))
# fan law: rpm per cfm by stage
s=df[(df.cfm>100)&(df.rpm>100)]; print('rpm/cfm by stage',(s.rpm/s.cfm).groupby(s.stage).median().round(3).to_dict())
# thermostat vs scb call
df['hotcall']=(df.w1>.5)|(df.w2>.5)|(df.e>.5); df['coolcall']=(df.y1>.5)|(df.y2>.5)
print('therm heat & scb heat agreement',round(((df.st>.9)==df.hotcall).mean(),3),'cool',round(((df.st<-.9)==df.coolcall).mean(),3))
df['mode']=np.where(df.hotcall,'heat',np.where(df.coolcall,'cool','off')); df['run']=(df['mode']!=df['mode'].shift()).cumsum(); df['age']=df.groupby('run').cumcount()
r=df[df['mode']!='off'].groupby('run').agg(mode=('mode','first'),n=('cfm','size'),w2=('w2','mean'),y2=('y2','mean'))
print(r.groupby('mode').agg(calls=('n','size'),med=('n','median'),p90=('n',lambda x:x.quantile(.9)),mins=('n','sum'),w2=('w2','mean'),y2=('y2','mean')).round(2))
df['others']=(df.kit.abs()>.3)|(df.grt.abs()>.3)
df['dTw']=df.wr-df.ws; df['gap']=df.ws-df.room
print('\nby age, heat alone'); h=df[(df['mode']=='heat')&~df.others]
print(h.groupby(pd.cut(h.age,[-1,1,3,5,8,12,20,40,400])).agg(n=('ws','size'),ws=('ws','median'),wr=('wr','median'),IN=('IN','median'),cfm=('cfm','median'),rpm=('rpm','median')).round(1))
print('by age, cool'); c=df[df['mode']=='cool']
print(c.groupby(pd.cut(c.age,[-1,1,3,5,8,12,20,40,400])).agg(n=('ws','size'),ws=('ws','median'),wr=('wr','median'),IN=('IN','median'),cfm=('cfm','median'),rpm=('rpm','median'),hpcool=('hpcool','mean')).round(1))
K={'heat':480,'cool':490}
for m,sel in (('heat',(df['mode']=='heat')&(df.hpheat>.9)&(df.hpcall>.9)&(df.gap>15)),('cool',(df['mode']=='cool')&(df.hpcool>.9)&(df.hpcall>.9)&(df.gap<-8))):
    for oth in (False,True):
        ss=df[sel&(df.age>=8)&(df.others==oth)]
        if not len(ss):continue
        g=ss.groupby('stage').agg(n=('ws','size'),ws=('ws','median'),wr=('wr','median'),dTw=('dTw','median'),room=('room','median'),gap=('gap','median'),cfm=('cfm','median'),rpm=('rpm','median'),out=('out','median'),rh=('rh','median')).round(2)
        print('\n',m,'others on loop:',oth);print(g)
        if not oth:
            for gpm in (6.5,7.4,7.8):
                q=K[m]*gpm*g.dTw.abs(); dta=q/(1.08*g.cfm); print(' GPM',gpm,'MBH',(q/1000).round(1).to_dict(),'est air dT',dta.round(1).to_dict(),'eps',(dta/g.gap.abs()).round(2).to_dict())
# duty
b=df[df.hpheat>.9].copy(); b['bin']=pd.cut(b.out,[30,40,45,50,55,60,70]); print('\n',b.groupby('bin').agg(mins=('out','size'),heat=('hotcall','mean'),w2=('w2','mean'),room=('room','mean'),others=('others','mean')).round(3))
print('cool share in cool mode',df[df.hpcool>.9].coolcall.mean().round(3),'of',(df.hpcool>.9).sum(),'rh',df.rh.median())
print('fan-only mins',(df.stage=='g').sum(),'off',(df.stage=='off').sum())
ny=lambda t:t.tz_convert('America/New_York').strftime('%m-%d %H:%M')
print('\ncool calls');
for rr,g in df[df['mode']=='cool'].groupby('run'):
    if len(g)<5: continue
    print(ny(g.index[0]),len(g),'hot-water min',int((g.ws>g.room).sum()),'peak ws',round(g.ws.max(),1),'room',round(g.room.iloc[0],1),round(g.room.max(),1),'y2',round(g.y2.mean(),2),'out',round(g.out.mean()))
# upstaging pairs in heat
ev=df.index[(df.w2>.5)&(df.w2.shift()<=.5)]; print('\nW2 rises',len(ev))
for t in ev[:12]:
    a=df[t-pd.Timedelta(minutes=8):t-pd.Timedelta(minutes=2)];b=df[t+pd.Timedelta(minutes=4):t+pd.Timedelta(minutes=12)]
    print(ny(t),'before',round(a.cfm.mean()),round(a.dTw.mean(),2),'after',round(b.cfm.mean()),round(b.dTw.mean(),2),'others',bool(a.others.any() or b.others.any()),'out',round(a.out.mean()))
df.to_pickle(D+'/u.pkl')
