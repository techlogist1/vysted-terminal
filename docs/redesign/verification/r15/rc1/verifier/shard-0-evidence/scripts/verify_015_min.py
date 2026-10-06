import asyncio, sys
sys.path.insert(0,'.')
exec(open(sys.argv[1]).read().split('async def main')[0])
async def main():
    await run("40.5% revenue growth\n", ['https://www.nseindia.com/get-quotes/equity?symbol=KAYNES'], {'ok':True,'text':'40.5% per NSE filing','citations':[{'url':'https://nsearchives.nseindia.com/corporate/KAYNES_results.pdf'}]}, '015 fresh minimal: one registrable domain (nseindia.com), one host per lane')
asyncio.run(main())
