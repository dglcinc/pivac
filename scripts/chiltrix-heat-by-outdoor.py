#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Chiller heating output, power, COP and duty by RedLink outdoor temperature.

Reads the per-minute CSVs from scripts/chiltrix-heat-fetch.sh. Keeps hours with the panel in heat
mode (HPHEAT) all hour and no boiler call (BLR), so the chiller carries the whole load. Heat is
flow x (outlet - inlet) for 25 % PG; power is the Emporia chiltrix circuit, so COP is all-in.
Room temperatures are Kelvin and heat setpoints degF. Usage: chiltrix-heat-by-outdoor.py DIR
"""
import csv,os,sys,collections,math
from datetime import datetime,timedelta
D=sys.argv[1]
def load(m):
    out={}
    for r in csv.reader(open(os.path.join(D,m+'.csv'))):
        if len(r)<5 or r[0].startswith('#') or r[3]=='_time' : continue
        try: out[r[3][:16]]=float(r[4])
        except: pass
    return out
names={'in':'hvac.chiller.chiltrix.inletTemp','out':'hvac.chiller.chiltrix.outletTemp','flow':'hvac.chiller.chiltrix.waterFlow',
'hz':'hvac.chiller.chiltrix.compressorHz','w':'electrical.emporia.house.chiltrix','oat':'environment.outside.thermostat.temperature',
'call':'electrical.ac.switch.utility.HPCALL.statenum','blr':'electrical.ac.switch.utility.BLR.statenum','dhwx':'electrical.ac.switch.utility.DHWX.statenum',
'heat':'electrical.ac.switch.utility.HPHEAT.statenum','gas':'hvac.boiler.sentry.gasInputValue'}
zones=['KIDS_ROOM','MASTER_BR','GREAT_ROOM','KITCHEN','DSTRS_FAM_ROOM']
S={k:load(v) for k,v in names.items()}
for z in zones:
    S['t_'+z]=load(f'environment.inside.thermostat.{z}.temperature'); S['s_'+z]=load(f'environment.inside.thermostat.{z}.heatset')
F=lambda k:(k-273.15)*1.8+32
hours=collections.defaultdict(list)
for t in sorted(S['hz']):
    row={k:S[k].get(t) for k in S}
    if None in (row['in'],row['out'],row['flow'],row['hz'],row['w'],row['oat'],row['heat'],row['blr']): continue
    est=datetime.fromisoformat(t)-timedelta(hours=5)
    hours[est.strftime('%Y-%m-%d %H')].append(row)
res=[]
for h,rows in sorted(hours.items()):
    if len(rows)<55: continue
    if min(r['heat'] for r in rows)<1: continue          # panel in heat mode all hour
    blr=sum(r['blr']>0.5 for r in rows)/len(rows)
    q=0;e=0;run=0
    for r in rows:
        dT=r['out']-r['in']; q+=r['flow']/60*1.02*3850*dT  # W
        e+=r['w']; run+= r['hz']>0
    n=len(rows); q/=n; e/=n
    short=min(min(F(r['t_'+z])-r['s_'+z] for z in zones if r['t_'+z] and r['s_'+z]) for r in rows)
    oat=F(sum(r['oat'] for r in rows)/n)
    res.append(dict(h=h,oat=oat,q=q*3.412/1000,e=e/1000,duty=run/n,blr=blr,call=sum(r['call']>0.5 for r in rows)/n,short=short))
# bins by outdoor
print('hours',len(res),'boiler hours',sum(r['blr']>0 for r in res))
bins=collections.defaultdict(list)
for r in res:
    if r['blr']==0: bins[int(math.floor(r['oat']/2)*2)].append(r)
print('%-6s %4s %7s %7s %6s %6s %6s %6s'%('OAT','hrs','kBTU/h','kW','COP','duty','>95%','short'))
for b in sorted(bins):
    L=bins[b]; Q=sum(x['q'] for x in L); E=sum(x['e'] for x in L)
    print('%2d-%2d  %4d %7.1f %7.2f %6.2f %6.2f %6d %6.1f'%(b,b+2,len(L),Q/len(L),E/len(L),Q/3.412/E if E else 0,sum(x['duty'] for x in L)/len(L),sum(x['duty']>0.95 for x in L),min(x['short'] for x in L)))
# full-duty hours: capacity
print('\nhours at >=90% duty:')
for r in sorted([r for r in res if r['duty']>=0.9 and r['blr']==0], key=lambda r:r['oat'])[:25]:
    print(r['h'],'%.1fF'%r['oat'],'%.1f kBTU/h'%r['q'],'COP %.2f'%(r['q']/3.412/r['e']),'duty %.2f'%r['duty'],'short %.1f'%r['short'])
