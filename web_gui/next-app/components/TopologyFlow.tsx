"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
  BackgroundVariant,
  Panel,
  Node,
  Edge,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import {
  ShieldAlert,
  Radio,
  Cpu,
  Lock,
  Unlock,
  Maximize,
  Minimize,
  RotateCcw,
  Network,
  ArrowRightLeft,
  Layers,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// -------------------------------------------------------------
// Custom Node: Software Component (SwC)
// -------------------------------------------------------------
const SwcCardNode = React.memo(({ data }: { data: any }) => {
  const isEntry = data.role === "entry";
  const isCritical = data.role === "critical";
  const shortName = data.label || data.id.split("/").pop();
  const ecuName = (data.ecu || "Unmapped").split("/").pop();

  return (
    <div
      className={`relative rounded-xl border px-3.5 py-2.5 shadow-lg transition-all min-w-[200px] max-w-[240px] text-left select-none ${
        isEntry
          ? "bg-slate-900/95 border-blue-500 shadow-blue-500/20 ring-1 ring-blue-500/40"
          : isCritical
          ? "bg-slate-900/95 border-rose-500 shadow-rose-500/20 ring-1 ring-rose-500/40"
          : "bg-slate-900/95 border-slate-700/80 hover:border-slate-500 shadow-black/40"
      }`}
    >
      <Handle
        type="target"
        position={data.targetPosition || Position.Left}
        className={`!w-3 !h-3 !border-2 ${
          isEntry
            ? "!bg-blue-500 !border-white"
            : isCritical
            ? "!bg-rose-500 !border-white"
            : "!bg-slate-400 !border-white"
        }`}
      />

      {/* Role Badge and Host ECU */}
      <div className="flex items-center justify-between gap-1 mb-1.5">
        {isEntry ? (
          <Badge className="bg-blue-950/80 text-blue-400 border-blue-800 text-[10px] font-mono gap-1 px-1.5 py-0 font-semibold">
            <Radio className="w-3 h-3 text-blue-400" /> ENTRY
          </Badge>
        ) : isCritical ? (
          <Badge className="bg-rose-950/80 text-rose-400 border-rose-800 text-[10px] font-mono gap-1 px-1.5 py-0 font-semibold">
            <ShieldAlert className="w-3 h-3 text-rose-400" /> ASIL-D
          </Badge>
        ) : (
          <Badge
            variant="secondary"
            className="bg-slate-800 text-slate-400 text-[10px] font-mono gap-1 px-1.5 py-0"
          >
            <Cpu className="w-3 h-3 text-slate-400" /> SwC
          </Badge>
        )}

        <span
          className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/70 truncate max-w-[100px]"
          title={`Host ECU: ${ecuName}`}
        >
          {ecuName}
        </span>
      </div>

      {/* Component Name */}
      <div className="font-bold text-xs text-slate-100 truncate" title={shortName}>
        {shortName}
      </div>

      <div
        className="text-[9px] font-mono text-slate-500 truncate mt-0.5"
        title={data.id}
      >
        {data.id}
      </div>

      <Handle
        type="source"
        position={data.sourcePosition || Position.Right}
        className={`!w-3 !h-3 !border-2 ${
          isEntry
            ? "!bg-blue-500 !border-white"
            : isCritical
            ? "!bg-rose-500 !border-white"
            : "!bg-slate-400 !border-white"
        }`}
      />
    </div>
  );
});

SwcCardNode.displayName = "SwcCardNode";

const nodeTypes = {
  swcNode: SwcCardNode,
};

// -------------------------------------------------------------
// Dagre Layout Engine
// -------------------------------------------------------------
function computeDagreLayout(
  nodes: Node[],
  edges: Edge[],
  direction: "LR" | "TB" = "LR"
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === "LR";
  dagreGraph.setGraph({
    rankdir: direction,
    ranksep: isHorizontal ? 120 : 90,
    nodesep: isHorizontal ? 50 : 60,
    align: "UL",
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 220, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      data: {
        ...node.data,
        targetPosition: isHorizontal ? Position.Left : Position.Top,
        sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      },
      position: {
        x: (nodeWithPosition?.x || 0) - 110,
        y: (nodeWithPosition?.y || 0) - 40,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

// -------------------------------------------------------------
// Main Topology Canvas Component
// -------------------------------------------------------------
interface TopologyFlowProps {
  graphData: any;
  secocData: any;
  graphVersion: "updated" | "before";
  isFullScreen: boolean;
  onToggleFullScreen: () => void;
  scenarioId: string;
}

function InnerTopologyFlow({
  graphData,
  secocData,
  graphVersion,
  isFullScreen,
  onToggleFullScreen,
  scenarioId,
}: TopologyFlowProps) {
  const [direction, setDirection] = useState<"LR" | "TB">("LR");
  const { fitView } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Build nodes and edges whenever inputs change
  useEffect(() => {
    if (!graphData || !secocData) return;

    const secocEdges = secocData.edges || [];
    const secocMap: Record<string, any> = {};
    secocEdges.forEach((e: any) => {
      secocMap[`${e.source}->${e.target}`] = e;
    });

    // Transform nodes
    const rawNodes: Node[] = (graphData.nodes || []).map((n: any) => ({
      id: n.id,
      type: "swcNode",
      data: {
        id: n.id,
        label: n.label,
        role: n.role,
        ecu: n.ecu,
      },
      position: { x: 0, y: 0 },
    }));

    // Transform edges
    const rawEdges: Edge[] = (graphData.edges || []).map((e: any, idx: number) => {
      const secInfo = secocMap[`${e.source}->${e.target}`];
      const connectorName = (e.connector || "").split("/").pop() || "connector";

      let strokeColor = "#64748b";
      let strokeWidth = 1.5;
      let strokeDasharray: string | undefined = undefined;
      let animated = false;
      let labelText = connectorName;
      let labelColor = "#334155";
      let labelBg = "#ffffff";
      let labelBorder = "#cbd5e1";

      if (secInfo) {
        if (secInfo.on_attack_path) {
          strokeColor = "#d97706";
          strokeWidth = 3.5;
          animated = true;
          labelText = `⚡ Attack: ${connectorName}`;
          labelColor = "#92400e";
          labelBg = "#fffbeb";
          labelBorder = "#f59e0b";
        } else if (secInfo.security_state === "AUTHENTICATED") {
          strokeColor = "#16a34a";
          strokeWidth = 2.2;
          labelText = `🔒 ${connectorName}`;
          labelColor = "#166534";
          labelBg = "#f0fdf4";
          labelBorder = "#22c55e";
        } else if (secInfo.security_state === "UNPROTECTED") {
          strokeColor = "#dc2626";
          strokeWidth = 2.8;
          strokeDasharray = "5 5";
          animated = true;
          labelText = `⚠️ ${connectorName}`;
          labelColor = "#991b1b";
          labelBg = "#fef2f2";
          labelBorder = "#ef4444";
        }
      }

      return {
        id: `e_${e.source}_${e.target}_${idx}`,
        source: e.source,
        target: e.target,
        type: "smoothstep",
        animated,
        label: labelText,
        labelStyle: {
          fill: labelColor,
          fontWeight: 600,
          fontSize: 10,
          fontFamily: "monospace",
        },
        labelBgStyle: {
          fill: labelBg,
          fillOpacity: 0.9,
          stroke: labelBorder,
          strokeWidth: 1,
          rx: 4,
          ry: 4,
        },
        labelBgPadding: [4, 6] as [number, number],
        style: {
          stroke: strokeColor,
          strokeWidth,
          strokeDasharray,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: strokeColor,
          width: 16,
          height: 16,
        },
      };
    });

    const layouted = computeDagreLayout(rawNodes, rawEdges, direction);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);

    setTimeout(() => {
      fitView({ padding: 0.2, duration: 400 });
    }, 100);
  }, [graphData, secocData, direction, fitView]);

  const toggleDirection = () => {
    setDirection((d) => (d === "LR" ? "TB" : "LR"));
  };

  const handleFit = useCallback(() => {
    fitView({ padding: 0.2, duration: 300 });
  }, [fitView]);

  return (
    <div className="relative w-full h-full flex flex-col">
      {/* Canvas Top Bar */}
      <div className="flex items-center justify-between mb-3 px-1 pb-2 border-b border-slate-800/80">
        <div className="flex items-center space-x-2">
          <Network className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-semibold text-slate-200">
            Topological Architecture Canvas (React Flow + Dagre)
          </span>
          <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
            {nodes.length} Nodes &bull; {edges.length} Edges
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Orientation Toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={toggleDirection}
            className="text-xs h-7 gap-1.5 bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200"
            title="Toggle Layout Orientation"
          >
            <ArrowRightLeft className="w-3.5 h-3.5 text-blue-400" />
            {direction === "LR" ? "Horizontal (L → R)" : "Vertical (T ↓ B)"}
          </Button>

          {/* Reset / Fit View */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleFit}
            className="text-xs h-7 gap-1 bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300"
            title="Fit Canvas to View"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-400" /> Fit View
          </Button>

          {/* Fullscreen / Minimize */}
          <Button
            variant="outline"
            size="sm"
            onClick={onToggleFullScreen}
            className={`text-xs h-7 gap-1.5 border-slate-700 ${
              isFullScreen
                ? "bg-slate-800 hover:bg-slate-700 text-amber-300 hover:text-amber-200"
                : "bg-slate-800 hover:bg-slate-700 text-blue-300 hover:text-blue-200"
            }`}
          >
            {isFullScreen ? (
              <>
                <Minimize className="w-3.5 h-3.5 text-amber-400" /> Minimize (Esc)
              </>
            ) : (
              <>
                <Maximize className="w-3.5 h-3.5 text-blue-400" /> Fullscreen
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Main Flow Canvas with White Background */}
      <div className="w-full flex-1 min-h-[500px] rounded-lg border border-slate-300 overflow-hidden bg-white shadow-sm">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          className="bg-white"
        >
          <Background
            color="#cbd5e1"
            gap={18}
            size={1.2}
            variant={BackgroundVariant.Dots}
          />
          <Controls className="!bg-white !border-slate-300 !shadow-md [&>button]:!bg-white [&>button]:!border-slate-200 [&>button]:!text-slate-700 [&>button:hover]:!bg-slate-100" />
          <MiniMap
            nodeStrokeWidth={3}
            nodeColor={(node: any) => {
              if (node.data?.role === "entry") return "#2563eb";
              if (node.data?.role === "critical") return "#dc2626";
              return "#64748b";
            }}
            maskColor="rgba(241, 245, 249, 0.75)"
            className="!bg-white/95 !border-slate-300 !rounded-lg overflow-hidden shadow-md"
          />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function TopologyFlow(props: TopologyFlowProps) {
  return (
    <ReactFlowProvider>
      <InnerTopologyFlow {...props} />
    </ReactFlowProvider>
  );
}
