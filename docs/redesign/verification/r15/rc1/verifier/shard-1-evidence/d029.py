import config
from services import yfinance_provider as y
for reg in ('IN','US'):
    tok=config.set_region(reg) if hasattr(config,'set_region') else None
    print(reg,[ (s,y._yahoo_symbol(s)) for s in ('RELIANCE.NS','532540.BO','BDL','INFY','SBIN','KSE','TATAMOTORS','JONJUA','BRK.B','AAPL')])
