import pandas as pd,numpy as np,glob,os,sys
D=sys.argv[1]
names={'environment.inside.hvac.ah.mbr.water.supply.temperature':'wsup','environment.inside.hvac.ah.mbr.water.return.temperature':'wret','environment.inside.hvac.ah.mbr.air.supply.temperature':'asup','environment.inside.hvac.ah.mbr.air.return.temperature':'aret','environment.inside.hvac.ah.mbr.y2':'y2','environment.inside.thermostat.MASTER_BR.statenum':'st','environment.inside.thermostat.MASTER_BR.temperature':'room','environment.inside.thermostat.MASTER_BR.heatset':'hset','environment.inside.thermostat.MASTER_BR.coolset':'cset','environment.inside.thermostat.MASTER_BR.humidity':'rh','environment.outside.thermostat.temperature':'out','environment.inside.hvac.LOOPA_SUP.temperature':'lsup','environment.inside.hvac.LOOPA_RET.temperature':'lret','environment.inside.hvac.IN.temperature':'IN','electrical.ac.switch.utility.HPCALL.statenum':'hpcall','electrical.ac.switch.utility.HPHEAT.statenum':'hpheat','electrical.ac.switch.utility.HPCOOL.statenum':'hpcool'}
fr={}
for m,n in names.items():
    d=pd.read_csv(f'{D}/{m}.csv',header=None,names=['t',n],parse_dates=['t']).set_index('t')[n]
    fr[n]=d
df=pd.DataFrame(fr).sort_index()
for c in ['wsup','wret','asup','aret','room','hset','cset','out','lsup','lret','IN']:
    print(c,'K?',round(df[c].median(),1)) if c in('wsup',) else None
    df[c]=df[c]*9/5-459.67 if df[c].median()>200 else df[c]
df.to_pickle(f'{D}/df.pkl')
print(df.index.min(),df.index.max(),len(df)); print(df.describe().T[['count','mean','min','max']].round(2))
print(df.st.round(2).value_counts().head(8))
print('hpheat frac',df.hpheat.mean().round(3),'hpcool frac',df.hpcool.mean().round(3))
