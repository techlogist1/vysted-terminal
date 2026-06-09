"use client";

/**
 * Node-editor panel — Phase-4 visual workflow surface.
 *
 * Hosts the react-flow canvas, the left palette, the right properties
 * panel, and the run overlay. Workflow specs round-trip through the
 * sidecar (`POST /workflow/save`, `GET /workflow/saved`, `POST
 * /workflow/run`) — no localStorage, sidecar-owned-persistence per
 * CLAUDE.md.
 *
 * Plugin-contributed node types (`VystedPlugin.contributesNodes`) are
 * read from `usePluginsStore.nodes` and unioned with the 10 built-in
 * types via `buildRegistry`.
 *
 * The drag-drop flow uses the HTML5 native drag API; the canvas drop
 * handler reads the `application/x-vysted-node-type` MIME the palette
 * stamps.
 *
 * The run lifecycle opens a `fetch` stream against `POST /workflow/run`,
 * parses each SSE frame, and reduces it into `RunOverlayState` via
 * `applyEvent`. The reduce is a pure function (testable without the
 * network).
 */

import "@xyflow/react/dist/style.css";

import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
  type OnConnect,
} from "@xyflow/react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type ReactNode,
} from "react";

import { Button } from "@/components/ui/button";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { usePluginsStore } from "@/store/plugins";

import type { WorkflowRunEvent, WorkflowSpec } from "../../../types/workflow";
import { CODE_NODE_ID, codeNodeBindings } from "./code-node";
import { CodeNodeInspector } from "./code-node-inspector";
import { evaluateCodeNodes, partitionWorkflow } from "./code-node-run";
import {
  coerceConfigValue,
  createFlowNode,
  FLOW_NODE_TYPE,
  flowToSpec,
  generateId,
  removeNodeAndEdges,
  specToFlow,
  updateNodeConfig,
  type FlowNodeData,
} from "./graph-state";
import { NodePalette, NODE_DRAG_MIME } from "./node-palette";
import {
  NODE_CONFIG_FIELDS,
  buildRegistry,
  defaultConfigFor,
  findEntry,
  type ConfigField,
  type RegistryEntry,
} from "./node-registry";
import { VystedNode } from "./VystedNode";
import { WorkflowSaveDialog, type SaveDialogValue } from "./workflow-save-dialog";
import {
  applyEvent,
  emptyOverlayState,
  WorkflowRunOverlay,
  type RunOverlayState,
} from "./workflow-run-overlay";

const NODE_TYPES: NodeTypes = { [FLOW_NODE_TYPE]: VystedNode };

const SNAP_GRID: [number, number] = [16, 16];

interface SavedSummary {
  id: string;
  name: string;
  description?: string;
  updatedAt: number;
}

// ---------------------------------------------------------------------------
// Provider wrapper
// ---------------------------------------------------------------------------

export function NodeEditorPanel() {
  return (
    <ReactFlowProvider>
      <NodeEditorPanelInner />
    </ReactFlowProvider>
  );
}

function NodeEditorPanelInner() {
  // --- Registry (built-in + plugin) -----------------------------------------
  const pluginNodes = usePluginsStore((s) => s.nodes);
  const registry: RegistryEntry[] = useMemo(() => buildRegistry(pluginNodes), [pluginNodes]);
  const resolveLabel = useCallback(
    (nodeTypeId: string): string => findEntry(registry, nodeTypeId)?.spec.label ?? nodeTypeId,
    [registry],
  );

  // --- Canvas state ---------------------------------------------------------
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // --- Identity (the workflow being edited) ---------------------------------
  const [workflowId, setWorkflowId] = useState<string>(() => generateId("wf"));
  const [workflowName, setWorkflowName] = useState<string>("Untitled workflow");
  const [workflowDescription, setWorkflowDescription] = useState<string>("");
  const [isDirty, setIsDirty] = useState<boolean>(false);

  // --- Save dialog ----------------------------------------------------------
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // --- Load dialog (a simple modal list) ------------------------------------
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [savedList, setSavedList] = useState<SavedSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // --- Run state ------------------------------------------------------------
  const [runState, setRunState] = useState<RunOverlayState>(emptyOverlayState);
  const runAbortRef = useRef<AbortController | null>(null);

  const { screenToFlowPosition } = useReactFlow();
  const reactFlowWrapper = useRef<HTMLDivElement | null>(null);

  // Wrap the react-flow change-callbacks so any mutation flips the dirty
  // flag — we deliberately avoid an effect-based watcher because the
  // React 19 `react-hooks/set-state-in-effect` rule rightly flags it as
  // a cascading re-render.
  const markDirty = useCallback(() => setIsDirty(true), []);
  const onNodesChangeWithDirty: typeof onNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      markDirty();
    },
    [markDirty, onNodesChange],
  );
  const onEdgesChangeWithDirty: typeof onEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);
      markDirty();
    },
    [markDirty, onEdgesChange],
  );

  // --- Drag-drop wiring -----------------------------------------------------
  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }, []);

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const nodeTypeId =
        event.dataTransfer.getData(NODE_DRAG_MIME) || event.dataTransfer.getData("text/plain");
      if (nodeTypeId === "") return;
      const entry = findEntry(registry, nodeTypeId);
      if (entry === undefined) return;
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const newNode = createFlowNode({
        id: generateId("node"),
        nodeTypeId: entry.spec.id,
        label: entry.spec.label,
        position,
        config: defaultConfigFor(entry.spec.id),
      });
      setNodes((prev) => [...prev, newNode]);
      markDirty();
    },
    [markDirty, registry, screenToFlowPosition, setNodes],
  );

  // --- Edge wiring ----------------------------------------------------------
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      setEdges((prev) =>
        addEdge(
          {
            ...connection,
            id: generateId("edge"),
          },
          prev,
        ),
      );
      // Connecting nodes mutates the workflow — flag dirty so the unsaved
      // badge shows and the user isn't silently losing the edge on close
      // (Phase 9.5). onNodesChange/onEdgesChange already do this; connect,
      // config-patch, and delete did not.
      markDirty();
    },
    [setEdges, markDirty],
  );

  // --- Selection ------------------------------------------------------------
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node<FlowNodeData>) => {
    setSelectedNodeId(node.id);
  }, []);
  const onPaneClick = useCallback(() => setSelectedNodeId(null), []);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );

  // --- Toolbar actions ------------------------------------------------------
  const handleNew = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setWorkflowId(generateId("wf"));
    setWorkflowName("Untitled workflow");
    setWorkflowDescription("");
    setSelectedNodeId(null);
    setRunState(emptyOverlayState());
    setIsDirty(false);
  }, [setEdges, setNodes]);

  const openSaveDialog = useCallback(() => {
    setSaveError(null);
    setSaveDialogOpen(true);
  }, []);

  const handleSave = useCallback(
    async (value: SaveDialogValue) => {
      setSaving(true);
      setSaveError(null);
      try {
        const spec = flowToSpec({
          id: workflowId,
          name: value.name,
          description: value.description !== "" ? value.description : undefined,
          nodes,
          edges,
        });
        const base = await getSidecarBaseUrl();
        const response = await fetch(new URL("/workflow/save", base).toString(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(spec),
        });
        if (!response.ok) {
          throw new Error(`save failed (${response.status})`);
        }
        const persisted = (await response.json()) as WorkflowSpec;
        setWorkflowId(persisted.id);
        setWorkflowName(persisted.name);
        setWorkflowDescription(persisted.description ?? "");
        setIsDirty(false);
        setSaveDialogOpen(false);
      } catch (error: unknown) {
        setSaveError(error instanceof Error ? error.message : "Save failed.");
      } finally {
        setSaving(false);
      }
    },
    [edges, nodes, workflowId],
  );

  const openLoadDialog = useCallback(async () => {
    setLoadError(null);
    setSavedList([]);
    setLoadingList(true);
    setLoadDialogOpen(true);
    try {
      const base = await getSidecarBaseUrl();
      const response = await fetch(new URL("/workflow/saved", base).toString());
      if (!response.ok) {
        throw new Error(`list failed (${response.status})`);
      }
      const payload = (await response.json()) as { workflows: WorkflowSpec[] };
      const summaries: SavedSummary[] = payload.workflows.map((spec) => ({
        id: spec.id,
        name: spec.name,
        description: spec.description,
        updatedAt: spec.updatedAt,
      }));
      setSavedList(summaries);
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : "Failed to list workflows.");
    } finally {
      setLoadingList(false);
    }
  }, []);

  const handleLoad = useCallback(
    async (id: string) => {
      setLoadError(null);
      try {
        const base = await getSidecarBaseUrl();
        const response = await fetch(
          new URL(`/workflow/saved/${encodeURIComponent(id)}`, base).toString(),
        );
        if (!response.ok) {
          throw new Error(`load failed (${response.status})`);
        }
        const spec = (await response.json()) as WorkflowSpec;
        const hydrated = specToFlow(spec, resolveLabel);
        setNodes(hydrated.nodes);
        setEdges(hydrated.edges);
        setWorkflowId(spec.id);
        setWorkflowName(spec.name);
        setWorkflowDescription(spec.description ?? "");
        setSelectedNodeId(null);
        setRunState(emptyOverlayState());
        setIsDirty(false);
        setLoadDialogOpen(false);
      } catch (error: unknown) {
        setLoadError(error instanceof Error ? error.message : "Load failed.");
      }
    },
    [resolveLabel, setEdges, setNodes],
  );

  // --- Run ------------------------------------------------------------------
  // HYBRID execution (R7 hackability): server nodes run in the sidecar
  // (`POST /workflow/run` SSE, services/workflow_engine.py); code nodes
  // (`transform.code`) evaluate CLIENT-side in the mathjs sandbox after the
  // server stream ends, fed by the streamed `node-output` outputs. See
  // `code-node-run.ts` for the partition + topological evaluation.
  const handleRun = useCallback(async () => {
    // Cancel any in-flight stream so a second click doesn't double-subscribe.
    if (runAbortRef.current !== null) {
      runAbortRef.current.abort();
    }
    const controller = new AbortController();
    runAbortRef.current = controller;
    const seededRows = nodes.map((n) => ({
      nodeId: n.id,
      nodeType: n.data.nodeTypeId,
      status: "pending" as const,
    }));
    const spec = flowToSpec({
      id: workflowId,
      name: workflowName,
      description: workflowDescription !== "" ? workflowDescription : undefined,
      nodes,
      edges,
    });
    const partition = partitionWorkflow(spec);
    if (partition.error !== undefined) {
      setRunState({ runId: null, status: "error", message: partition.error, nodes: seededRows });
      return;
    }
    setRunState({ runId: null, status: "running", nodes: seededRows });
    const startedMark = performance.now();
    const outputsByNode = new Map<string, Record<string, unknown>>();
    const failedServerIds: string[] = [];
    // The engine validates BEFORE emitting run-start (`_validate_spec` is
    // the first statement of `run_workflow`) and routers/workflow.py
    // swallows the exception, so a rejected spec — unregistered plugin node
    // type, dangling edge ref — closes the SSE stream with ZERO frames.
    // Track whether a terminal frame ever arrived; its absence is a run
    // failure, never a green "ok" over a board of pending rows.
    let serverTerminalSeen = false;
    let serverErrorMessage: string | null = null;
    let runId = generateId("local");
    try {
      if (partition.server.nodes.length > 0) {
        const base = await getSidecarBaseUrl();
        const response = await fetch(new URL("/workflow/run", base).toString(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec: partition.server, mode: "full" }),
          signal: controller.signal,
        });
        if (!response.ok || response.body === null) {
          throw new Error(`run failed (${response.status})`);
        }
        await consumeSse(response.body, (event) => {
          switch (event.kind) {
            case "run-start":
              // Adopt the server's run id WITHOUT the reducer's node-list
              // reset, so the code-node rows stay visible as pending while
              // the server wave runs.
              runId = event.runId;
              setRunState((prev) => ({
                ...prev,
                runId: event.runId,
                status: "running",
                startedAt: event.startedAt,
              }));
              return;
            case "node-output":
              outputsByNode.set(event.nodeId, event.outputs);
              break;
            case "node-error":
              failedServerIds.push(event.nodeId);
              break;
            case "run-complete":
              // Held — the run isn't over until the code nodes evaluated;
              // server-side failures are folded into the final event below.
              serverTerminalSeen = true;
              return;
            case "run-error":
              // Held like run-complete, but keep the engine's message so an
              // engine-level failure that produced no node-error frames
              // still surfaces instead of folding into a fake success.
              serverTerminalSeen = true;
              serverErrorMessage = event.message;
              return;
            default:
              break;
          }
          setRunState((prev) => applyEvent(prev, event));
        });
        if (controller.signal.aborted) {
          return;
        }
        if (!serverTerminalSeen) {
          throw new Error(
            "workflow stream ended without a terminal frame — the sidecar " +
              "rejected the spec before starting (e.g. a node type with no " +
              "server-side handler) or crashed mid-run",
          );
        }
      } else {
        // Pure-code workflow — no sidecar round-trip at all.
        setRunState((prev) => ({ ...prev, runId, startedAt: Date.now() }));
      }
      const { failedNodeIds } = evaluateCodeNodes(
        spec,
        partition.codeOrder,
        outputsByNode,
        runId,
        (event) => setRunState((prev) => applyEvent(prev, event)),
      );
      const durationMs = performance.now() - startedMark;
      const allFailed = [...failedServerIds, ...failedNodeIds];
      const failureMessage =
        allFailed.length > 0
          ? `failures in nodes: ${JSON.stringify([...allFailed].sort())}`
          : serverErrorMessage;
      setRunState((prev) =>
        applyEvent(
          prev,
          failureMessage !== null
            ? { kind: "run-error", runId, message: failureMessage, durationMs }
            : { kind: "run-complete", runId, durationMs },
        ),
      );
    } catch (error: unknown) {
      if (controller.signal.aborted) {
        return;
      }
      const message = error instanceof Error ? error.message : "Run failed.";
      setRunState((prev) => ({
        ...prev,
        status: "error",
        message,
      }));
    } finally {
      if (runAbortRef.current === controller) {
        runAbortRef.current = null;
      }
    }
  }, [edges, nodes, workflowDescription, workflowId, workflowName]);

  const handleCloseOverlay = useCallback(() => {
    if (runAbortRef.current !== null) {
      runAbortRef.current.abort();
      runAbortRef.current = null;
    }
    setRunState(emptyOverlayState());
  }, []);

  // Cleanup the in-flight stream when the panel unmounts.
  useEffect(() => {
    return () => {
      if (runAbortRef.current !== null) {
        runAbortRef.current.abort();
      }
    };
  }, []);

  // --- Render ---------------------------------------------------------------
  return (
    <div data-testid="node-editor-panel" className="bg-charcoal-900 flex h-full w-full flex-col">
      {/* Toolbar */}
      <header className="border-charcoal-700 flex items-center justify-between gap-2 border-b px-3 py-2">
        <div className="flex min-w-0 flex-1 items-baseline gap-3">
          <h2 className="text-charcoal-100 text-panel-title font-mono tracking-wide uppercase">
            Node Editor
          </h2>
          <input
            aria-label="Workflow name"
            value={workflowName}
            onChange={(event) => {
              setWorkflowName(event.target.value);
              setIsDirty(true);
            }}
            className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-control text-caption focus:ring-charcoal-500 h-8 max-w-xs flex-1 border px-2 font-mono outline-none focus:ring-1"
          />
          {isDirty && (
            <span className="text-charcoal-400 text-micro font-mono uppercase">unsaved</span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Button size="sm" variant="ghost" onClick={handleNew}>
            New
          </Button>
          <Button size="sm" variant="ghost" onClick={openLoadDialog}>
            Load
          </Button>
          <Button size="sm" variant="outline" onClick={openSaveDialog}>
            Save
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleRun}
            disabled={nodes.length === 0 || runState.status === "running"}
          >
            {runState.status === "running" ? "Running…" : "Run"}
          </Button>
        </div>
      </header>

      {/* Body */}
      <div className="flex min-h-0 flex-1">
        <NodePalette registry={registry} />

        <div
          ref={reactFlowWrapper}
          className="relative min-w-0 flex-1"
          onDrop={onDrop}
          onDragOver={onDragOver}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChangeWithDirty}
            onEdgesChange={onEdgesChangeWithDirty}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={NODE_TYPES}
            snapToGrid
            snapGrid={SNAP_GRID}
            fitView
            proOptions={{ hideAttribution: true }}
            className="h-full w-full"
          >
            {/* ReactFlow's Background dots aren't CSS-themed — pin them to the
                warm-graphite palette (charcoal-900 canvas, charcoal-700 dots).
                Keep in lockstep with tokens.css (FR-030). */}
            <Background gap={16} size={1} color="#39332b" bgColor="#1a1814" />
            <Controls position="bottom-right" />
          </ReactFlow>
          {nodes.length === 0 && (
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2">
              <span className="text-charcoal-500 text-caption font-mono">Empty workflow</span>
              <span className="text-charcoal-600 text-micro font-mono">
                Drag a node from the palette to start
              </span>
            </div>
          )}

          {/* Run overlay rides over the canvas as an absolute drawer rather than
              consuming a third flex rail — three rails would starve the canvas
              below the panel's min width. */}
          {runState.status !== "idle" && (
            <div className="absolute top-2 right-2 bottom-2 z-10">
              <WorkflowRunOverlay
                state={runState}
                onClose={handleCloseOverlay}
                onRerun={runState.status !== "running" ? handleRun : undefined}
              />
            </div>
          )}
        </div>

        <PropertiesPanel
          node={selectedNode}
          onPatch={(patch) => {
            if (selectedNode === null) return;
            setNodes((prev) => updateNodeConfig(prev, selectedNode.id, patch));
            // Code-node binding edits change the node's input PORTS — prune
            // edges that now target a removed/renamed port so the spec never
            // carries a dangling targetPort.
            if (selectedNode.data.nodeTypeId === CODE_NODE_ID && Array.isArray(patch["inputs"])) {
              const kept = new Set(codeNodeBindings(patch));
              setEdges((prev) =>
                prev.filter((e) => e.target !== selectedNode.id || kept.has(e.targetHandle ?? "")),
              );
            }
            markDirty(); // config edits are unsaved mutations too (Phase 9.5)
          }}
          onDelete={() => {
            if (selectedNode === null) return;
            setNodes((prev) => removeNodeAndEdges(prev, edges, selectedNode.id).nodes);
            setEdges((prev) => removeNodeAndEdges(nodes, prev, selectedNode.id).edges);
            setSelectedNodeId(null);
            markDirty(); // node deletion is an unsaved mutation (Phase 9.5)
          }}
        />
      </div>

      {/* Save dialog */}
      <WorkflowSaveDialog
        open={saveDialogOpen}
        initialValue={{ name: workflowName, description: workflowDescription }}
        mode={isDirty ? "update" : "create"}
        saving={saving}
        error={saveError}
        onClose={() => setSaveDialogOpen(false)}
        onSubmit={handleSave}
      />

      {/* Load dialog */}
      {loadDialogOpen && (
        <LoadDialog
          summaries={savedList}
          loadingList={loadingList}
          error={loadError}
          onClose={() => setLoadDialogOpen(false)}
          onPick={handleLoad}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Properties panel — right rail
// ---------------------------------------------------------------------------

interface PropertiesPanelProps {
  node: Node<FlowNodeData> | null;
  onPatch: (patch: Record<string, unknown>) => void;
  onDelete: () => void;
}

function PropertiesPanel({ node, onPatch, onDelete }: PropertiesPanelProps) {
  return (
    <aside
      data-testid="properties-panel"
      className="border-charcoal-700 bg-charcoal-900 flex h-full w-64 min-w-64 flex-col border-l"
    >
      <header className="border-charcoal-700 flex items-baseline justify-between border-b px-3 py-2">
        <span className="text-charcoal-200 text-caption font-mono uppercase">Properties</span>
      </header>
      <div className="flex-1 overflow-y-auto p-3">
        {node === null ? (
          <p className="text-charcoal-500 text-caption font-mono">
            Select a node on the canvas to edit its configuration.
          </p>
        ) : (
          <PropertiesForm node={node} onPatch={onPatch} onDelete={onDelete} />
        )}
      </div>
    </aside>
  );
}

function PropertiesForm({
  node,
  onPatch,
  onDelete,
}: PropertiesPanelProps & { node: Node<FlowNodeData> }) {
  const nodeTypeId = node.data.nodeTypeId;
  const fields = NODE_CONFIG_FIELDS[nodeTypeId];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <span className="text-charcoal-400 text-micro font-mono uppercase">Type</span>
        <span className="text-charcoal-100 text-caption font-mono">{nodeTypeId}</span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-charcoal-400 text-micro font-mono uppercase">ID</span>
        <span className="text-charcoal-200 text-micro truncate font-mono">{node.id}</span>
      </div>
      {nodeTypeId === CODE_NODE_ID ? (
        <CodeNodeInspector config={node.data.config} onPatch={onPatch} />
      ) : fields !== undefined && fields.length > 0 ? (
        fields.map((field) => (
          <ConfigFieldEditor
            key={field.key}
            field={field}
            value={node.data.config[field.key]}
            onChange={(value) => onPatch({ [field.key]: value })}
          />
        ))
      ) : fields !== undefined ? (
        <p className="text-charcoal-500 text-micro font-mono">No configuration for this node.</p>
      ) : (
        <FreeFormConfigEditor config={node.data.config} onReplace={onPatch} />
      )}
      <div className="mt-2 flex justify-end">
        <Button size="sm" variant="ghost" onClick={onDelete}>
          Delete node
        </Button>
      </div>
    </div>
  );
}

function ConfigFieldEditor({
  field,
  value,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const rawValue =
    value === undefined || value === null
      ? ""
      : typeof value === "boolean"
        ? String(value)
        : String(value);
  let control: ReactNode;
  if (field.kind === "select" && field.options !== undefined) {
    control = (
      <select
        aria-label={field.label}
        value={rawValue}
        onChange={(event) => onChange(event.target.value)}
        className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 h-8 w-full px-2 font-mono outline-none focus:ring-1"
      >
        <option value="">—</option>
        {field.options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  } else if (field.kind === "textarea") {
    control = (
      <textarea
        aria-label={field.label}
        value={rawValue}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        placeholder={field.placeholder}
        className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 min-h-[4rem] resize-y p-2 font-mono outline-none focus:ring-1"
      />
    );
  } else if (field.kind === "boolean") {
    control = (
      <select
        aria-label={field.label}
        value={rawValue || "false"}
        onChange={(event) => onChange(coerceConfigValue("boolean", event.target.value, value))}
        className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 h-8 w-full px-2 font-mono outline-none focus:ring-1"
      >
        <option value="false">false</option>
        <option value="true">true</option>
      </select>
    );
  } else {
    control = (
      <input
        aria-label={field.label}
        type={field.kind === "number" ? "number" : "text"}
        value={rawValue}
        onChange={(event) => onChange(coerceConfigValue(field.kind, event.target.value, value))}
        placeholder={field.placeholder}
        className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 h-8 px-2 font-mono outline-none focus:ring-1"
      />
    );
  }
  return (
    <label className="flex flex-col gap-1">
      <span className="text-charcoal-400 text-micro font-mono uppercase">{field.label}</span>
      {control}
    </label>
  );
}

function FreeFormConfigEditor({
  config,
  onReplace,
}: {
  config: Record<string, unknown>;
  onReplace: (patch: Record<string, unknown>) => void;
}) {
  const [draft, setDraft] = useState(() => {
    try {
      return JSON.stringify(config, null, 2);
    } catch {
      return "{}";
    }
  });
  const [error, setError] = useState<string | null>(null);

  const apply = () => {
    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>;
      onReplace(parsed);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid JSON");
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <span className="text-charcoal-400 text-micro font-mono uppercase">Config (JSON)</span>
      <textarea
        aria-label="Config JSON"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        rows={6}
        className="bg-charcoal-800 text-charcoal-100 rounded-control text-micro min-h-[6rem] resize-y p-2 font-mono outline-none"
      />
      {error !== null && <span className="text-negative text-micro font-mono">{error}</span>}
      <Button size="sm" variant="outline" onClick={apply}>
        Apply
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Load dialog
// ---------------------------------------------------------------------------

interface LoadDialogProps {
  summaries: readonly SavedSummary[];
  loadingList: boolean;
  error: string | null;
  onClose: () => void;
  onPick: (id: string) => void;
}

function LoadDialog({ summaries, loadingList, error, onClose, onPick }: LoadDialogProps) {
  // Close on Escape — the dialog is a hand-rolled modal (no Radix), so wire the
  // keyboard dismissal explicitly while it's mounted.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      data-testid="workflow-load-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workflow-load-dialog-title"
      onClick={onClose}
      className="bg-charcoal-950/60 fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="bg-charcoal-900 border-charcoal-700 flex w-[460px] flex-col gap-3 rounded-none border p-4"
      >
        <header className="flex items-baseline justify-between">
          <h2
            id="workflow-load-dialog-title"
            className="text-charcoal-100 text-panel-title font-mono tracking-wide uppercase"
          >
            Load workflow
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close load dialog"
            className="text-charcoal-400 text-body hover:text-charcoal-100 font-mono"
          >
            ×
          </button>
        </header>
        {error !== null && <p className="text-negative text-micro font-mono">{error}</p>}
        {loadingList ? (
          <p className="text-charcoal-400 text-caption animate-pulse font-mono">
            Fetching workflows…
          </p>
        ) : summaries.length === 0 ? (
          <p className="text-charcoal-400 text-caption font-mono">No saved workflows yet.</p>
        ) : (
          <ul className="flex max-h-72 flex-col gap-1 overflow-y-auto">
            {summaries.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => onPick(s.id)}
                  className={cn(
                    "border-charcoal-700 hover:border-charcoal-500 hover:bg-charcoal-700/5",
                    "rounded-control text-caption w-full border px-2 py-1.5 text-left font-mono",
                  )}
                >
                  <div className="text-charcoal-100">{s.name}</div>
                  {s.description !== undefined && s.description !== "" && (
                    <div className="text-charcoal-400 text-micro truncate">{s.description}</div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SSE consumer
// ---------------------------------------------------------------------------

async function consumeSse(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: WorkflowRunEvent) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const frame = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        const dataLine = frame
          .split("\n")
          .map((line) => (line.startsWith("data:") ? line.slice(5).trim() : ""))
          .filter((line) => line.length > 0)
          .join("");
        if (dataLine !== "") {
          try {
            const event = JSON.parse(dataLine) as WorkflowRunEvent;
            onEvent(event);
          } catch (err) {
            // The engine should never emit malformed frames; surface it so a
            // dropped run event isn't completely silent (Phase 9.5).
            console.warn("workflow SSE: dropping malformed frame", err);
          }
        }
        separator = buffer.indexOf("\n\n");
      }
    }
  } finally {
    // Always release the lock — on a throw/abort mid-stream the previous code
    // leaked the locked reader, wedging the ReadableStream (Phase 9.5).
    reader.releaseLock();
  }
}
