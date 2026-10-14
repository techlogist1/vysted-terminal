import sys, json
sys.path.insert(0,'.')
from services import agent_runtime as ar
from services.llm import get_provider
from services.agent_tools.schemas import openai_tools
from models.llm import LLMMessage
spec=ar.get_agent('copilot'); tools=list(spec.tools)
ad=get_provider('ollama'); win=ad.context_window('llama3.1:8b')
sysp=spec.system_prompt if hasattr(spec,'system_prompt') else ''
print('window',win,'all tools',len(tools),'schema tok',len(json.dumps(openai_tools(tools)))//4,'sys tok',len(sysp)//4)
for prompt in ["What's the P/E of RELIANCE?",
               "Compare fundamentals and news for TCS and INFY, check SEC filings for INFY, pull the macro series for India CPI, screen for small caps, backtest a momentum strategy on my portfolio and chart it with RSI",
               "Research Kaynes Technology in depth"]:
    msgs=[LLMMessage(role='system',content=sysp),LLMMessage(role='user',content=prompt)]
    sub=ar._window_tool_subset(tools,msgs,win)
    est=ar._estimate_tokens(msgs,sub)
    print(f'{len(sub):2d} tools, est {est} tok ({est/win:.0%} of window) :: {prompt[:50]}')
big='x'*200000
c=ar._model_facing_content('web_search', big, win); print('cap on window lane:', len(c), c[win*4//8: win*4//8+80])
c2=ar._model_facing_content('fundamentals', big, None); print('cap hosted:', len(c2))
import itertools
for NAMES in (['fundamentals','news'],['fundamentals','news','web_search']):
 print('--- round with',len(NAMES),'tool results')
 for prompt in ["What's the P/E of RELIANCE and its latest news?",
                "Compare fundamentals and news for TCS and INFY, check SEC filings for INFY, pull the macro series for India CPI, screen for small caps, backtest a momentum strategy on my portfolio and chart it with RSI"]:
     msgs=[LLMMessage(role='system',content=sysp),LLMMessage(role='user',content=prompt)]
     sub=ar._window_tool_subset(tools,msgs,win)
     calls=[{'id':f'c{i}','name':n,'arguments':'{}'} for i,n in enumerate(NAMES)]
     msgs.append(LLMMessage(role='assistant',content='',metadata={'tool_calls':calls}))
     for c in calls:
         msgs.append(LLMMessage(role='tool',content=ar._model_facing_content(c['name'],'y'*60000,win),metadata={'tool_call_id':c['id'],'name':c['name']}))
     ar._fit_to_window(msgs,sub,win)
     est=ar._estimate_tokens(msgs,sub)
     print(f'{len(sub)} tools; after fit est {est} tok vs window {win} (answer reserve leaves {win-win//8}) -> {"OVER" if est>win-win//8 else "fits"}; over num_ctx: {est>win}')
