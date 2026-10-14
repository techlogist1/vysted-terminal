import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sidecar"))
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand/sidecar")
os.environ.setdefault("VYSTED_DATA_DIR", "/tmp/battery15work/wfdata")
os.makedirs("/tmp/battery15work/wfdata", exist_ok=True)

from models.workflow import WorkflowEdge, WorkflowNode, WorkflowRunEvent, WorkflowSpec
from services import workflow_engine, workflow_nodes
from services.workflow_nodes import builtin

def node(nid, t, config=None):
    return WorkflowNode(id=nid, type=t, position={"x":0.0,"y":0.0}, config=config or {})

def edge(eid, s, t, sport="out", tport="in"):
    return WorkflowEdge(id=eid, sourceNode=s, sourcePort=sport, targetNode=t, targetPort=tport)

def spec(nodes, edges):
    return WorkflowSpec(id="probe-wf", name="probe", nodes=nodes, edges=edges)

async def main():
    print("=== R15-CODE-PLATFORM-004: logic.branch truthiness of falsy strings ===")
    for val in ["false", "no", "0", "off"]:
        out = await builtin.logic_branch({"value": val}, {})
        print(f"  value={val!r} -> {out}")

    print()
    print("=== R15-CODE-PLATFORM-004: engine skip propagation (un-taken port) ===")
    workflow_engine.reset_registry_for_tests()
    workflow_nodes.register_all()
    events = []
    async def on_event(e):
        events.append(e)
    s = spec(
        [node("branch","logic.branch"), node("notify","action.notify_desktop"),
         node("log","action.log"), node("taken","action.log")],
        [edge("e1","branch","notify","false_path","value"),
         edge("e2","notify","log","message","value"),
         edge("e3","branch","taken","true_path","value")],
    )
    result = await workflow_engine.run_workflow(s, inputs={"value":"yes"}, on_event=on_event)
    by_id = {n.node_id: n for n in result.nodes}
    print("  run status:", result.status)
    print("  notify.status:", by_id["notify"].status)
    print("  log.status (two hops down un-taken port):", by_id["log"].status)
    print("  taken.status:", by_id["taken"].status)
    print("  branch.outputs:", by_id["branch"].outputs)
    skipped_events = {e.node_id for e in events if e.kind == "node-skipped"}
    print("  node-skipped events:", skipped_events)

    print()
    print("=== R15-CODE-PLATFORM-019: FIRST_COMPLETED release + per-node timeout ===")
    release_a = asyncio.Event()
    c_started = asyncio.Event()
    timings = {}
    t0 = asyncio.get_event_loop().time()

    async def _slow(_inputs, _config):
        await asyncio.sleep(4.0)
        return {"out": "a"}
    async def _fast(_inputs, _config):
        return {"out": "b"}
    async def _dep(inputs, _config):
        timings["c_start"] = asyncio.get_event_loop().time() - t0
        c_started.set()
        return {"out": inputs.get("in")}

    workflow_engine.register_node_type("slow019", _slow)
    workflow_engine.register_node_type("fast019", _fast)
    workflow_engine.register_node_type("dep019", _dep)
    s2 = spec(
        [node("a","slow019"), node("b","fast019"), node("c","dep019")],
        [edge("e1","b","c")],
    )
    run = asyncio.create_task(workflow_engine.run_workflow(s2))
    await asyncio.wait_for(c_started.wait(), timeout=6)
    print(f"  c started at t={timings['c_start']:.2f}s while a (4s sleep) still running: run.done()={run.done()}")
    result2 = await run
    t_end = asyncio.get_event_loop().time() - t0
    print(f"  run finished at t={t_end:.2f}s, status={result2.status}")

    print()
    print("=== R15-CODE-PLATFORM-019: per-node timeout produces node-error ===")
    async def _hang(_inputs, _config):
        await asyncio.Event().wait()
        return {}
    workflow_engine.register_node_type("hang019", _hang)
    workflow_engine.register_node_type("t019", _fast)
    s3 = spec(
        [node("h","hang019", {"timeout_seconds": 2}), node("d","t019")],
        [edge("e1","h","d")],
    )
    t0b = asyncio.get_event_loop().time()
    result3 = await asyncio.wait_for(workflow_engine.run_workflow(s3), timeout=10)
    t_end_b = asyncio.get_event_loop().time() - t0b
    by_id3 = {n.node_id: n for n in result3.nodes}
    print(f"  h.status={by_id3['h'].status} h.error={by_id3['h'].error!r} elapsed={t_end_b:.2f}s")

asyncio.run(main())
