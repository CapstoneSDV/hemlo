"use client";

import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  ShieldAlert,
  Play,
  FolderOpen,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Ban,
  Radio,
  Network,
  Lock,
  Unlock,
  Layers,
  ChevronRight,
  Cpu,
  Route,
  Activity,
  FileCode2,
  Maximize,
  Minimize,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from "lucide-react";
import TopologyFlow from "@/components/TopologyFlow";

interface Scenario {
  id: string;
  title: string;
  path: string;
}

export default function PipelineApp() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState("01_jeep_uconnect");
  const [pipelineData, setPipelineData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [graphVersion, setGraphVersion] = useState<"updated" | "before">("updated");
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  // Upload state
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [rolesFile, setRolesFile] = useState<File | null>(null);

  useEffect(() => {
    fetchScenarios();
  }, []);

  useEffect(() => {
    if (selectedScenario) {
      runPipeline(selectedScenario);
    }
  }, [selectedScenario]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullScreen) {
        setIsFullScreen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullScreen]);

  const fetchScenarios = async () => {
    try {
      const res = await fetch("/api/pipeline?action=scenarios");
      const data = await res.json();
      if (Array.isArray(data)) {
        setScenarios(data);
      }
    } catch (e) {
      console.error("Failed to fetch scenarios:", e);
    }
  };

  const runPipeline = async (scId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/pipeline?scenario=${scId}`);
      const data = await res.json();
      if (data.error) {
        alert("Pipeline error: " + data.error);
      } else {
        setPipelineData(data);
      }
    } catch (e: any) {
      alert("Execution failed: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomUpload = async () => {
    if (!beforeFile || !afterFile) {
      alert("Please select both Before and After ARXML files.");
      return;
    }
    setLoading(true);
    setUploadOpen(false);
    try {
      const beforeText = await beforeFile.text();
      const afterText = await afterFile.text();
      const rolesText = rolesFile ? await rolesFile.text() : "";

      const res = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          before_content: beforeText,
          after_content: afterText,
          roles_content: rolesText,
        }),
      });

      const data = await res.json();
      if (data.error) {
        alert("Upload run failed: " + data.error);
      } else {
        setPipelineData(data);
        const customId = `Custom: ${beforeFile.name} -> ${afterFile.name}`;
        setSelectedScenario(customId);
        setCurrentStep(1);
      }
    } catch (e: any) {
      alert("Custom upload error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const s1 = pipelineData?.stage1_parse;
  const s2 = pipelineData?.stage2_graph;
  const s3 = pipelineData?.stage3_secoc;
  const s4 = pipelineData?.stage4_reachability;
  const s5 = pipelineData?.stage5_gate;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col font-sans">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold shadow-lg shadow-blue-500/20">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base font-semibold leading-none tracking-tight flex items-center gap-2">
                ARXML SecDiff
                <Badge variant="outline" className="text-[10px] text-blue-400 border-blue-500/30">
                  Release Gate
                </Badge>
              </h1>
              <p className="text-xs text-slate-400 mt-1">ISO/SAE 21434 & ASIL Automotive Security Verification</p>
            </div>
          </div>

          {/* Scenario Selector & Custom Upload Modal */}
          <div className="flex items-center space-x-3">
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 max-w-xs truncate"
            >
              {scenarios.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.id}: {sc.title}
                </option>
              ))}
            </select>

            <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
              <DialogTrigger className="inline-flex items-center justify-center gap-1.5 rounded-md text-xs font-medium border border-slate-700 bg-slate-800 hover:bg-slate-700 h-8 px-3 text-slate-100 cursor-pointer transition-colors shadow-sm">
                <FolderOpen className="w-3.5 h-3.5 text-blue-400" />
                Browse Local Files
              </DialogTrigger>
              <DialogContent className="bg-slate-900 border-slate-800 text-slate-50">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <FolderOpen className="w-5 h-5 text-blue-400" />
                    Browse & Upload Local ARXML Files
                  </DialogTitle>
                  <DialogDescription className="text-slate-400 text-xs">
                    Select your before/baseline and after/updated ARXML files to run step-by-step security diffing.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2 text-xs">
                  <div>
                    <label className="block font-medium mb-1.5">Before ARXML (Baseline Release):</label>
                    <input
                      type="file"
                      accept=".arxml,.xml"
                      onChange={(e) => setBeforeFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-300"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-1.5">After ARXML (Proposed Release):</label>
                    <input
                      type="file"
                      accept=".arxml,.xml"
                      onChange={(e) => setAfterFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-300"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-1.5">Roles Config (YAML - Optional):</label>
                    <input
                      type="file"
                      accept=".yaml,.yml"
                      onChange={(e) => setRolesFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-300"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="ghost" size="sm" onClick={() => setUploadOpen(false)}>
                    Cancel
                  </Button>
                  <Button size="sm" className="bg-blue-600 hover:bg-blue-500 text-white" onClick={handleCustomUpload}>
                    Execute Pipeline
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Button
              size="sm"
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs gap-1.5 shadow"
              onClick={() => runPipeline(selectedScenario)}
              disabled={loading}
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loading ? "Running..." : "Run Pipeline"}
            </Button>
          </div>
        </div>
      </header>

      {/* Bidirectional Pipeline Stepper Bar */}
      <nav className="border-b border-slate-800 bg-slate-900/40 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2 overflow-x-auto py-1">
            {[
              { num: 1, title: "Parse & Index" },
              { num: 2, title: "Graph Build" },
              { num: 3, title: "SecOC Annotation" },
              { num: 4, title: "Diff & Reachability" },
              { num: 5, title: "Gate Decision" },
            ].map((step, idx) => {
              const active = currentStep === step.num;
              const passed = currentStep > step.num;
              return (
                <React.Fragment key={step.num}>
                  <button
                    onClick={() => setCurrentStep(step.num)}
                    className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      active
                        ? "bg-blue-600 text-white shadow"
                        : passed
                        ? "text-emerald-400 hover:bg-slate-800"
                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                    }`}
                  >
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${
                        active
                          ? "border-white bg-blue-700"
                          : passed
                          ? "border-emerald-400 text-emerald-400"
                          : "border-slate-700"
                      }`}
                    >
                      {step.num}
                    </span>
                    <span>{step.title}</span>
                  </button>
                  {idx < 4 && <ChevronRight className="w-4 h-4 text-slate-700 shrink-0" />}
                </React.Fragment>
              );
            })}
          </div>

          <div className="flex items-center space-x-2 ml-4 shrink-0">
            <Button
              variant="outline"
              size="sm"
              disabled={currentStep === 1}
              onClick={() => setCurrentStep((s) => s - 1)}
              className="text-xs gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Prev Step
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={currentStep === 5}
              onClick={() => setCurrentStep((s) => s + 1)}
              className="text-xs gap-1"
            >
              Next Step <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </nav>

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-slate-400">
            <Activity className="w-8 h-8 animate-spin text-blue-500 mb-3" />
            <p className="text-sm">Processing AUTOSAR AST & Graph Pipeline...</p>
          </div>
        )}

        {!loading && pipelineData && (
          <>
            {/* STAGE 1: PARSE & INDEX */}
            {currentStep === 1 && s1 && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge variant="outline" className="text-blue-400 border-blue-500/30 mb-1">
                      Stage 1 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight">ARXML AST Parsing & Path Indexing</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Recursively parses the AUTOSAR XML DOM into an absolute-path element hash index.
                    </p>
                  </div>
                  <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1.5 py-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Unresolved References: 0
                  </Badge>
                </div>

                {/* Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-400">Component Prototypes</CardDescription>
                      <CardTitle className="text-2xl font-bold text-white flex justify-between items-baseline">
                        {s1.updated.prototypes}
                        <span className="text-xs font-normal text-slate-500">Before: {s1.before.prototypes}</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-400">Assembly Connectors</CardDescription>
                      <CardTitle className="text-2xl font-bold text-white flex justify-between items-baseline">
                        {s1.updated.assembly_connectors}
                        <span className="text-xs font-normal text-slate-500">Before: {s1.before.assembly_connectors}</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-400">Physical ECUs</CardDescription>
                      <CardTitle className="text-2xl font-bold text-white flex justify-between items-baseline">
                        {s1.updated.ecus}
                        <span className="text-xs font-normal text-slate-500">Hardware Nodes</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-400">Network PDUs</CardDescription>
                      <CardTitle className="text-2xl font-bold text-white flex justify-between items-baseline">
                        {s1.updated.pdus}
                        <span className="text-xs font-normal text-slate-500">Signals: {s1.updated.system_signals}</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                </div>

                {/* Table */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader className="py-3 px-4 border-b border-slate-800">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold">Indexed Component Prototypes & Host Bindings</CardTitle>
                      <span className="text-xs text-slate-400 font-mono">SWC-TO-ECU-MAPPING</span>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0 max-h-80 overflow-y-auto">
                    <Table>
                      <TableHeader className="bg-slate-800/50 sticky top-0">
                        <TableRow className="border-slate-800">
                          <TableHead className="text-xs">Prototype</TableHead>
                          <TableHead className="text-xs">Host ECU</TableHead>
                          <TableHead className="text-xs">AUTOSAR Path</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="divide-y divide-slate-800 text-xs font-mono">
                        {s1.updated.prototype_list.map((p: any) => (
                          <TableRow key={p.path} className="border-slate-800 hover:bg-slate-800/40">
                            <TableCell className="font-semibold text-white">{p.short_name}</TableCell>
                            <TableCell>
                              <Badge variant="secondary" className="bg-slate-800 text-slate-300 font-normal">
                                {p.ecu.split("/").pop()}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-slate-400 truncate max-w-sm">{p.path}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* STAGE 2: GRAPH BUILD */}
            {currentStep === 2 && s2 && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge variant="outline" className="text-blue-400 border-blue-500/30 mb-1">
                      Stage 2 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight">Topological Graph Construction</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Visualizes the directed MultiDiGraph G = (V, E) with color-coded nodes and hardware ECU clusters.
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      size="sm"
                      variant={graphVersion === "updated" ? "default" : "outline"}
                      onClick={() => setGraphVersion("updated")}
                      className="text-xs h-7"
                    >
                      After Snapshot
                    </Button>
                    <Button
                      size="sm"
                      variant={graphVersion === "before" ? "default" : "outline"}
                      onClick={() => setGraphVersion("before")}
                      className="text-xs h-7"
                    >
                      Before Snapshot
                    </Button>
                  </div>
                </div>

                {/* Color Legend */}
                <div className="flex flex-wrap items-center gap-4 p-3 rounded-lg border border-slate-800 bg-slate-900 text-xs">
                  <span className="font-semibold text-slate-400">Legend:</span>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3.5 h-3.5 rounded bg-blue-300 border border-blue-600 inline-block"></span>
                    <span className="text-slate-200">Entry Point (Wireless / OBD)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3.5 h-3.5 rounded bg-red-300 border border-red-600 inline-block"></span>
                    <span className="text-slate-200">Safety Target (ASIL-D)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3.5 h-3.5 rounded bg-slate-200 border border-slate-400 inline-block"></span>
                    <span className="text-slate-200">Standard SwC</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-6 h-0.5 bg-emerald-500 inline-block"></span>
                    <span className="text-emerald-400">Authenticated (SecOC)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-6 h-0.5 border-b-2 border-dashed border-rose-500 inline-block"></span>
                    <span className="text-rose-400">Unprotected Bus</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-6 h-1 bg-amber-500 inline-block"></span>
                    <span className="text-amber-400 font-bold">Attack Route</span>
                  </div>
                </div>

                {/* Canvas & Edge List */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div
                    className={
                      isFullScreen
                        ? "fixed inset-0 z-50 bg-slate-950 p-6 flex flex-col w-screen h-screen"
                        : "lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900 p-3 shadow-lg flex flex-col h-[600px]"
                    }
                  >
                    <TopologyFlow
                      graphData={s2[graphVersion]}
                      secocData={s3[graphVersion]}
                      graphVersion={graphVersion}
                      isFullScreen={isFullScreen}
                      onToggleFullScreen={() => setIsFullScreen((prev) => !prev)}
                      scenarioId={selectedScenario}
                    />
                  </div>

                  <Card className="bg-slate-900 border-slate-800 flex flex-col h-[570px]">
                    <CardHeader className="py-3 px-4 border-b border-slate-800">
                      <CardTitle className="text-sm font-semibold">Connectors Edge List</CardTitle>
                      <CardDescription className="text-xs text-slate-400">
                        Extracted assembly connectors from composition
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-3 overflow-y-auto space-y-2 flex-1">
                      {s2[graphVersion].edges.map((e: any, idx: number) => (
                        <div key={idx} className="p-2 rounded bg-slate-800/40 border border-slate-800 text-xs font-mono">
                          <div className="flex items-center justify-between text-white font-semibold">
                            <span>
                              {e.source.split("/").pop()} &rarr; {e.target.split("/").pop()}
                            </span>
                            <span className="text-[10px] text-slate-400 uppercase font-sans">{e.influence}</span>
                          </div>
                          <p className="text-[11px] text-slate-400 truncate mt-0.5">{e.connector}</p>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {/* STAGE 3: SECOC ANNOTATION */}
            {currentStep === 3 && s3 && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge variant="outline" className="text-blue-400 border-blue-500/30 mb-1">
                      Stage 3 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight">3-Valued SecOC Wire Annotation</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Determines physical wire security by tracing each connector down to its carrying I-PDU.
                    </p>
                  </div>
                </div>

                {/* 3 Metric Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card className="bg-slate-900 border-slate-800 border-l-4 border-l-slate-500">
                    <CardHeader className="py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-slate-300">RTE_LOCAL (None)</span>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {s3.updated.local_count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Connectors remain within the same physical ECU. No physical wire frame is created.
                      </p>
                    </CardHeader>
                  </Card>

                  <Card className="bg-slate-900 border-slate-800 border-l-4 border-l-emerald-500">
                    <CardHeader className="py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-emerald-400">AUTHENTICATED (True)</span>
                        <Badge variant="outline" className="font-mono text-xs text-emerald-400 border-emerald-500/30">
                          {s3.updated.authenticated_count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Cross-ECU bus traffic wrapped in SECURED-I-PDU with cryptographic freshness and MAC.
                      </p>
                    </CardHeader>
                  </Card>

                  <Card className="bg-slate-900 border-slate-800 border-l-4 border-l-rose-500">
                    <CardHeader className="py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-rose-400">UNPROTECTED (False)</span>
                        <Badge variant="outline" className="font-mono text-xs text-rose-400 border-rose-500/30">
                          {s3.updated.unprotected_count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Cross-ECU bus traffic without SecOC. Raw payload exposed to frame injection/tampering.
                      </p>
                    </CardHeader>
                  </Card>
                </div>

                {/* Table */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader className="py-3 px-4 border-b border-slate-800">
                    <CardTitle className="text-sm font-semibold">Vehicle Communication Security Matrix</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 max-h-96 overflow-y-auto">
                    <Table>
                      <TableHeader className="bg-slate-800/50 sticky top-0">
                        <TableRow className="border-slate-800 text-xs">
                          <TableHead>Connector</TableHead>
                          <TableHead>Source &rarr; Target</TableHead>
                          <TableHead>Boundary</TableHead>
                          <TableHead>Security State</TableHead>
                          <TableHead>Carrying PDUs</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="divide-y divide-slate-800 text-xs font-mono">
                        {s3.updated.edges.map((e: any, idx: number) => (
                          <TableRow key={idx} className="border-slate-800 hover:bg-slate-800/40">
                            <TableCell className="font-semibold text-white">{e.connector}</TableCell>
                            <TableCell className="text-slate-300">
                              {e.source.split("/").pop()} &rarr; {e.target.split("/").pop()}
                            </TableCell>
                            <TableCell className="text-slate-400">{e.bus_visible ? "Bus Wire" : "Internal Memory"}</TableCell>
                            <TableCell>
                              {e.security_state === "AUTHENTICATED" && (
                                <Badge className="bg-emerald-950 text-emerald-400 border-emerald-800 text-[10px]">
                                  AUTHENTICATED 🔒
                                </Badge>
                              )}
                              {e.security_state === "UNPROTECTED" && (
                                <Badge className="bg-rose-950 text-rose-400 border-rose-800 text-[10px]">
                                  UNPROTECTED ⚠️
                                </Badge>
                              )}
                              {e.security_state === "RTE_LOCAL" && (
                                <Badge variant="secondary" className="bg-slate-800 text-slate-400 text-[10px]">
                                  RTE_LOCAL
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-slate-400">{e.pdus.join(", ") || "None"}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* STAGE 4: DIFF & REACHABILITY */}
            {currentStep === 4 && s4 && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge variant="outline" className="text-blue-400 border-blue-500/30 mb-1">
                      Stage 4 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight">Dual-Graph Diff & Transitive Attack Reachability</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Executes constrained DFS reachability analysis from untrusted entry nodes to ASIL-D critical targets.
                    </p>
                  </div>
                </div>

                {/* Seeds Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="py-3 px-4 border-b border-slate-800">
                      <CardTitle className="text-xs font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                        <Radio className="w-3.5 h-3.5" /> Untrusted Entry Points (S)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-3 flex flex-wrap gap-2">
                      {s4.roles.entry_points.map((ep: any) => (
                        <Badge key={ep.node} variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30 font-mono text-xs">
                          {ep.label}
                        </Badge>
                      ))}
                    </CardContent>
                  </Card>

                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="py-3 px-4 border-b border-slate-800">
                      <CardTitle className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5" /> Safety-Critical Targets (T)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-3 flex flex-wrap gap-2">
                      {s4.roles.critical_targets.map((ct: any) => (
                        <Badge key={ct.node} variant="outline" className="bg-rose-500/10 text-rose-400 border-rose-500/30 font-mono text-xs">
                          {ct.label} (ASIL-{ct.asil})
                        </Badge>
                      ))}
                    </CardContent>
                  </Card>
                </div>

                {/* Discovered Attack Paths */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader className="py-3 px-4 border-b border-slate-800 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-semibold">Newly Opened Attack Chains (&Delta;R)</CardTitle>
                    <Badge variant="outline" className="text-rose-400 border-rose-500/30 font-mono text-xs">
                      {s4.reachability.new_paths.length} Transitive Path(s)
                    </Badge>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {s4.reachability.new_paths.length === 0 ? (
                      <p className="text-xs text-slate-400">Zero new attack reachability paths opened in this release.</p>
                    ) : (
                      s4.reachability.new_paths.map((p: any, idx: number) => (
                        <div key={idx} className="p-3 rounded-lg border border-rose-900/60 bg-rose-950/20 space-y-2">
                          <div className="flex items-center justify-between text-xs font-semibold text-rose-300">
                            <span className="flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" /> Attack Route #{idx + 1} ({p.hops.length} Hops)
                            </span>
                            <Badge variant="outline" className="bg-rose-950 border-rose-800 text-rose-400 text-[10px]">
                              {p.unprotected ? "Unprotected Bus Hop Included" : "Secured"}
                            </Badge>
                          </div>
                          <div className="font-mono text-xs flex items-center flex-wrap gap-2 pt-1 text-slate-200">
                            {p.nodes.map((n: string, i: number) => (
                              <React.Fragment key={i}>
                                <span className={i === 0 ? "text-blue-400 font-bold" : i === p.nodes.length - 1 ? "text-rose-400 font-bold" : "text-slate-300"}>
                                  {n}
                                </span>
                                {i < p.nodes.length - 1 && <span className="text-slate-500">&rarr;</span>}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {/* STAGE 5: GATE DECISION */}
            {currentStep === 5 && s5 && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge variant="outline" className="text-blue-400 border-blue-500/30 mb-1">
                      Stage 5 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight">ISO/SAE 21434 Risk Scoring & Release Gate</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Synthesizes target ASIL safety impact and attack feasibility into an automated release verdict.
                    </p>
                  </div>
                </div>

                {/* Verdict Hero Card */}
                <Card
                  className={`p-6 border shadow-xl ${
                    s5.verdict === "BLOCK"
                      ? "border-rose-900 bg-rose-950/30"
                      : s5.verdict === "FLAG"
                      ? "border-amber-900 bg-amber-950/30"
                      : "border-emerald-900 bg-emerald-950/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div
                        className={`h-12 w-12 rounded-xl flex items-center justify-center text-white shadow-lg ${
                          s5.verdict === "BLOCK"
                            ? "bg-rose-600 shadow-rose-600/30"
                            : s5.verdict === "FLAG"
                            ? "bg-amber-600 shadow-amber-600/30"
                            : "bg-emerald-600 shadow-emerald-600/30"
                        }`}
                      >
                        {s5.verdict === "BLOCK" ? <Ban className="w-6 h-6" /> : <CheckCircle2 className="w-6 h-6" />}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span
                            className={`text-2xl font-black tracking-wider uppercase ${
                              s5.verdict === "BLOCK"
                                ? "text-rose-400"
                                : s5.verdict === "FLAG"
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {s5.verdict}
                          </span>
                          <Badge variant="secondary" className="font-mono text-xs">
                            exit code: {s5.exit_code}
                          </Badge>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          {s5.verdict === "BLOCK"
                            ? "Release Rejected: Safety-critical ASIL-D actuators are reachable via unprotected bus traffic."
                            : s5.verdict === "FLAG"
                            ? "Manual Review Required: Moderate architectural changes detected."
                            : "Release Approved: Clean release, zero newly reachable safety targets over unprotected links."}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-6">
                      <div className="text-right">
                        <p className="text-xs text-slate-400">Risk 5 / Severe</p>
                        <p className="text-2xl font-bold font-mono text-rose-400">{s5.risk_breakdown.risk_5}</p>
                      </div>
                      <Separator orientation="vertical" className="h-10 bg-slate-800" />
                      <div className="text-right">
                        <p className="text-xs text-slate-400">Total Findings</p>
                        <p className="text-2xl font-bold font-mono text-white">{s5.findings.length}</p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Findings List */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader className="py-3 px-4 border-b border-slate-800">
                    <CardTitle className="text-sm font-semibold">Audit Findings & Evidence Trace</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {s5.findings.map((f: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-slate-800 bg-slate-950 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Badge
                              className={`text-[10px] font-mono font-bold ${
                                f.risk >= 4 ? "bg-rose-950 text-rose-400 border-rose-800" : "bg-amber-950 text-amber-400 border-amber-800"
                              }`}
                            >
                              RISK {f.risk} [{f.impact}/{f.feasibility}]
                            </Badge>
                            <span className="text-xs font-semibold text-white">{f.title}</span>
                          </div>
                          <span className="text-[10px] font-mono text-slate-500 uppercase">{f.category}</span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed">{f.detail}</p>
                        {f.rationale.length > 0 && (
                          <div className="text-[11px] font-mono text-slate-400 bg-slate-900 p-2.5 rounded border border-slate-800/80">
                            {f.rationale.join(" • ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-4 px-6 text-center text-xs text-slate-500 bg-slate-900/30">
        ARXML SecDiff Next.js App &bull; Powered by shadcn/ui &bull; Automated Cybersecurity Release Gate
      </footer>
    </div>
  );
}
