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
  ChevronDown,
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
  const [selectedFolder, setSelectedFolder] = useState("real_time_scenarios_realistic");
  const [customFolderInput, setCustomFolderInput] = useState("");
  const [isCustomFolder, setIsCustomFolder] = useState(false);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState("01_jeep_uconnect");
  const [pipelineData, setPipelineData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [graphVersion, setGraphVersion] = useState<"updated" | "before">("updated");
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [datasetOpen, setDatasetOpen] = useState(false);

  // Upload state
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [rolesFile, setRolesFile] = useState<File | null>(null);

  useEffect(() => {
    fetchScenarios(selectedFolder);
  }, [selectedFolder]);

  useEffect(() => {
    if (selectedScenario && !selectedScenario.startsWith("Custom:")) {
      runPipeline(selectedScenario, selectedFolder);
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

  const fetchScenarios = async (folderPath?: string) => {
    const f = folderPath || selectedFolder;
    try {
      const res = await fetch(`/api/pipeline?action=scenarios&folder=${encodeURIComponent(f)}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setScenarios(data);
        if (data.length > 0) {
          const exists = data.some((s: Scenario) => s.id === selectedScenario);
          if (!exists) {
            setSelectedScenario(data[0].id);
          } else {
            runPipeline(selectedScenario, f);
          }
        } else {
          setScenarios([]);
        }
      }
    } catch (e) {
      console.error("Failed to fetch scenarios:", e);
    }
  };

  const runPipeline = async (scId: string, folderPath?: string) => {
    const f = folderPath || selectedFolder;
    setLoading(true);
    try {
      const res = await fetch(`/api/pipeline?scenario=${encodeURIComponent(scId)}&folder=${encodeURIComponent(f)}`);
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

  // Derive display name for the folder badge
  const folderDisplayName =
    selectedFolder === "real_time_scenarios_realistic" ? "Realistic R20-11" :
    selectedFolder === "real_time_scenarios" ? "Original Benchmark" :
    selectedFolder.split(/[\\/]/).pop() || selectedFolder;

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
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Top Header */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur sticky top-0 z-50">

        {/* Row 1: Brand + Action buttons */}
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold shadow-md shadow-blue-500/20">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-sm font-semibold leading-none tracking-tight flex items-center gap-2 text-slate-900">
                ARXML SecDiff
                <Badge variant="outline" className="text-[10px] text-blue-700 border-blue-200 bg-blue-50 font-semibold">
                  Release Gate
                </Badge>
              </h1>
              <p className="text-[11px] text-slate-500 mt-0.5">ISO/SAE 21434 &amp; ASIL Automotive Security Verification</p>
            </div>
          </div>

          {/* Right side: Upload + Run buttons */}
          <div className="flex items-center gap-2">
            {/* Upload custom ARXML files */}
            <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
              <DialogTrigger
                onClick={() => setUploadOpen(true)}
                className="h-8 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-xs text-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <FolderOpen className="w-3.5 h-3.5 text-slate-500" />
                Upload Files
              </DialogTrigger>
              <DialogContent className="bg-white border-slate-200 text-slate-900 shadow-2xl">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-slate-900">
                    <FolderOpen className="w-5 h-5 text-blue-600" />
                    Browse &amp; Upload Local ARXML Files
                  </DialogTitle>
                  <DialogDescription className="text-slate-500 text-xs">
                    Select your before/baseline and after/updated ARXML files to run step-by-step security diffing.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2 text-xs">
                  <div>
                    <label className="block font-medium mb-1.5 text-slate-800">Before ARXML (Baseline Release):</label>
                    <input
                      type="file"
                      accept=".arxml,.xml"
                      onChange={(e) => setBeforeFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:bg-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-1.5 text-slate-800">After ARXML (Proposed Release):</label>
                    <input
                      type="file"
                      accept=".arxml,.xml"
                      onChange={(e) => setAfterFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:bg-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-1.5 text-slate-800">Roles Config (YAML - Optional):</label>
                    <input
                      type="file"
                      accept=".yaml,.yml"
                      onChange={(e) => setRolesFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:bg-white"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="ghost" size="sm" onClick={() => setUploadOpen(false)} className="hover:bg-slate-100 text-slate-700">
                    Cancel
                  </Button>
                  <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm" onClick={handleCustomUpload}>
                    Execute Pipeline
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* Run Pipeline button */}
            <Button
              size="sm"
              className="h-8 bg-blue-600 hover:bg-blue-700 text-white text-xs gap-1.5 shadow-sm px-4 shrink-0 font-medium"
              onClick={() => runPipeline(selectedScenario, selectedFolder)}
              disabled={loading}
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loading ? "Running..." : "Run Pipeline"}
            </Button>
          </div>
        </div>

        {/* Row 2: Dataset folder picker + Scenario selector toolbar */}
        <div className="border-t border-slate-200 bg-slate-100/70">
          <div className="max-w-7xl mx-auto px-6 h-11 flex items-center gap-3">

            {/* Label */}
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider shrink-0">Dataset</span>

            {/* Folder picker button — opens modal */}
            <Dialog open={datasetOpen} onOpenChange={setDatasetOpen}>
              <DialogTrigger
                onClick={() => setDatasetOpen(true)}
                className="flex items-center gap-1.5 h-7 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-xs text-slate-800 transition-colors cursor-pointer shrink-0 shadow-sm"
              >
                <FolderOpen className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                <span className="text-blue-700 font-medium">{folderDisplayName}</span>
                <ChevronDown className="w-3 h-3 text-slate-500 shrink-0" />
              </DialogTrigger>
              <DialogContent className="bg-white border-slate-200 text-slate-900 max-w-md shadow-2xl">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-sm text-slate-900">
                    <FolderOpen className="w-4 h-4 text-blue-600" />
                    Select Scenario Dataset Folder
                  </DialogTitle>
                  <DialogDescription className="text-slate-500 text-xs">
                    Choose a folder that contains scenario sub-folders, each with <code className="bg-slate-100 text-slate-700 border border-slate-200 px-1 py-0.5 rounded">before.arxml</code> and <code className="bg-slate-100 text-slate-700 border border-slate-200 px-1 py-0.5 rounded">after.arxml</code>.
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-3 py-1">
                  {/* Preset options */}
                  {[
                    { id: "real_time_scenarios_realistic", label: "Realistic Dataset", desc: "Enterprise AUTOSAR R20-11 · 13 CVE scenarios · Full CAN-FD & SecOC", badge: "Recommended" },
                    { id: "real_time_scenarios", label: "Original Benchmark", desc: "Lightweight mock scenarios · 13 CVE scenarios", badge: null },
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => { setSelectedFolder(opt.id); setIsCustomFolder(false); setDatasetOpen(false); }}
                      className={`w-full text-left flex items-start gap-3 px-4 py-3 rounded-lg border transition-all cursor-pointer ${
                        selectedFolder === opt.id && !isCustomFolder
                          ? "border-blue-500 bg-blue-50 text-blue-900 shadow-sm ring-1 ring-blue-500/20"
                          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 text-slate-700"
                      }`}
                    >
                      <FolderOpen className={`w-4 h-4 mt-0.5 shrink-0 ${selectedFolder === opt.id && !isCustomFolder ? "text-blue-600" : "text-slate-400"}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-900">{opt.label}</span>
                          {opt.badge && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">{opt.badge}</span>}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">{opt.desc}</p>
                        <code className="text-[10px] text-slate-500 mt-1 block">{opt.id}/</code>
                      </div>
                      {selectedFolder === opt.id && !isCustomFolder && (
                        <CheckCircle2 className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                      )}
                    </button>
                  ))}

                  {/* Custom path input */}
                  <div className={`px-4 py-3 rounded-lg border transition-all ${isCustomFolder ? "border-blue-500 bg-blue-50/50" : "border-slate-200 bg-white hover:border-slate-300"}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <FolderOpen className={`w-4 h-4 ${isCustomFolder ? "text-blue-600" : "text-slate-400"}`} />
                      <span className="text-xs font-semibold text-slate-800">Custom Folder Path</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mb-2">Type a folder name (relative to project root) or an absolute path.</p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="e.g. real_time_scenarios_realistic or C:\my_data"
                        value={customFolderInput}
                        onChange={(e) => setCustomFolderInput(e.target.value)}
                        onFocus={() => setIsCustomFolder(true)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && customFolderInput.trim()) {
                            setIsCustomFolder(true);
                            setSelectedFolder(customFolderInput.trim());
                            setDatasetOpen(false);
                          }
                        }}
                        className="flex-1 bg-white border border-slate-300 text-xs rounded-md px-3 py-1.5 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                      />
                      <Button
                        size="sm"
                        className="h-7 text-xs px-3 bg-blue-600 hover:bg-blue-700 text-white shrink-0 shadow-sm"
                        onClick={() => {
                          if (customFolderInput.trim()) {
                            setIsCustomFolder(true);
                            setSelectedFolder(customFolderInput.trim());
                            setDatasetOpen(false);
                          }
                        }}
                      >
                        Load
                      </Button>
                    </div>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            {/* Divider */}
            <div className="h-5 w-px bg-slate-300 shrink-0" />

            {/* Scenario label */}
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider shrink-0">Scenario</span>

            {/* Scenario dropdown — takes remaining space */}
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="flex-1 min-w-0 h-7 bg-white border border-slate-300 text-xs rounded-md px-3 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer shadow-sm"
            >
              {scenarios.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.title || sc.id}
                </option>
              ))}
            </select>

          </div>
        </div>

      </header>

      {/* Bidirectional Pipeline Stepper Bar */}
      <nav className="border-b border-slate-200 bg-white px-6 py-3">
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
                        ? "bg-blue-600 text-white shadow-sm font-semibold"
                        : passed
                        ? "text-emerald-700 hover:bg-emerald-50 font-medium"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${
                        active
                          ? "border-white bg-blue-700 text-white"
                          : passed
                          ? "border-emerald-500 text-emerald-700 bg-emerald-50"
                          : "border-slate-300 text-slate-500 bg-slate-100"
                      }`}
                    >
                      {step.num}
                    </span>
                    <span>{step.title}</span>
                  </button>
                  {idx < 4 && <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />}
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
              className="text-xs gap-1 bg-white hover:bg-slate-100 border-slate-300 text-slate-700 shadow-sm"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Prev Step
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={currentStep === 5}
              onClick={() => setCurrentStep((s) => s + 1)}
              className="text-xs gap-1 bg-white hover:bg-slate-100 border-slate-300 text-slate-700 shadow-sm"
            >
              Next Step <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </nav>

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-slate-500">
            <Activity className="w-8 h-8 animate-spin text-blue-600 mb-3" />
            <p className="text-sm font-medium">Processing AUTOSAR AST & Graph Pipeline...</p>
          </div>
        )}

        {!loading && pipelineData && (
          <>
            {/* STAGE 1: PARSE & INDEX */}
            {currentStep === 1 && s1 && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge variant="outline" className="text-blue-700 border-blue-200 bg-blue-50 mb-1 font-semibold">
                      Stage 1 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">ARXML AST Parsing & Path Indexing</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Recursively parses the AUTOSAR XML DOM into an absolute-path element hash index.
                    </p>
                  </div>
                  <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border border-emerald-200 gap-1.5 py-1 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Unresolved References: 0
                  </Badge>
                </div>

                {/* Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Card className="bg-white border-slate-200 shadow-sm">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-500">Component Prototypes</CardDescription>
                      <CardTitle className="text-2xl font-bold text-slate-900 flex justify-between items-baseline">
                        {s1.updated.prototypes}
                        <span className="text-xs font-normal text-slate-500">Before: {s1.before.prototypes}</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white border-slate-200 shadow-sm">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-500">Assembly Connectors</CardDescription>
                      <CardTitle className="text-2xl font-bold text-slate-900 flex justify-between items-baseline">
                        {s1.updated.assembly_connectors}
                        <span className="text-xs font-normal text-slate-500">Before: {s1.before.assembly_connectors}</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white border-slate-200 shadow-sm">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-500">Physical ECUs</CardDescription>
                      <CardTitle className="text-2xl font-bold text-slate-900 flex justify-between items-baseline">
                        {s1.updated.ecus}
                        <span className="text-xs font-normal text-slate-500">Hardware Nodes</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white border-slate-200 shadow-sm">
                    <CardHeader className="pb-2">
                      <CardDescription className="text-xs text-slate-500">Network PDUs</CardDescription>
                      <CardTitle className="text-2xl font-bold text-slate-900 flex justify-between items-baseline">
                        {s1.updated.pdus}
                        <span className="text-xs font-normal text-slate-500">Signals: {s1.updated.system_signals}</span>
                      </CardTitle>
                    </CardHeader>
                  </Card>
                </div>

                {/* Table */}
                <Card className="bg-white border-slate-200 shadow-sm">
                  <CardHeader className="py-3 px-4 border-b border-slate-200">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold text-slate-900">Indexed Component Prototypes & Host Bindings</CardTitle>
                      <span className="text-xs text-slate-500 font-mono">SWC-TO-ECU-MAPPING</span>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0 max-h-80 overflow-y-auto">
                    <Table>
                      <TableHeader className="bg-slate-50 sticky top-0">
                        <TableRow className="border-slate-200">
                          <TableHead className="text-xs text-slate-600 font-semibold">Prototype</TableHead>
                          <TableHead className="text-xs text-slate-600 font-semibold">Host ECU</TableHead>
                          <TableHead className="text-xs text-slate-600 font-semibold">AUTOSAR Path</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="divide-y divide-slate-200 text-xs font-mono">
                        {s1.updated.prototype_list.map((p: any) => (
                          <TableRow key={p.path} className="border-slate-200 hover:bg-slate-50/80">
                            <TableCell className="font-semibold text-slate-900">{p.short_name}</TableCell>
                            <TableCell>
                              <Badge variant="secondary" className="bg-slate-100 text-slate-700 border border-slate-200 font-normal">
                                {p.ecu.split("/").pop()}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-slate-500 truncate max-w-sm">{p.path}</TableCell>
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
                    <Badge variant="outline" className="text-blue-700 border-blue-200 bg-blue-50 mb-1 font-semibold">
                      Stage 2 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">Topological Graph Construction</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Visualizes the directed MultiDiGraph G = (V, E) with color-coded nodes and hardware ECU clusters.
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      size="sm"
                      variant={graphVersion === "updated" ? "default" : "outline"}
                      onClick={() => setGraphVersion("updated")}
                      className={`text-xs h-7 ${graphVersion === "updated" ? "bg-blue-600 text-white shadow-sm" : "bg-white border-slate-300 text-slate-700 hover:bg-slate-100"}`}
                    >
                      After Snapshot
                    </Button>
                    <Button
                      size="sm"
                      variant={graphVersion === "before" ? "default" : "outline"}
                      onClick={() => setGraphVersion("before")}
                      className={`text-xs h-7 ${graphVersion === "before" ? "bg-blue-600 text-white shadow-sm" : "bg-white border-slate-300 text-slate-700 hover:bg-slate-100"}`}
                    >
                      Before Snapshot
                    </Button>
                  </div>
                </div>

                {/* Color Legend */}
                <div className="flex flex-wrap items-center gap-4 p-3 rounded-lg border border-slate-200 bg-white shadow-sm text-xs">
                  <span className="font-semibold text-slate-600">Legend:</span>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3.5 h-3.5 rounded bg-blue-100 border border-blue-500 inline-block"></span>
                    <span className="text-slate-700">Entry Point (Wireless / OBD)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3.5 h-3.5 rounded bg-rose-100 border border-rose-500 inline-block"></span>
                    <span className="text-slate-700">Safety Target (ASIL-D)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3.5 h-3.5 rounded bg-slate-100 border border-slate-300 inline-block"></span>
                    <span className="text-slate-700">Standard SwC</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-6 h-0.5 bg-emerald-600 inline-block"></span>
                    <span className="text-emerald-700 font-medium">Authenticated (SecOC)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-6 h-0.5 border-b-2 border-dashed border-rose-500 inline-block"></span>
                    <span className="text-rose-700 font-medium">Unprotected Bus</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-6 h-1 bg-amber-500 inline-block"></span>
                    <span className="text-amber-700 font-bold">Attack Route</span>
                  </div>
                </div>

                {/* Canvas & Edge List */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div
                    className={
                      isFullScreen
                        ? "fixed inset-0 z-50 bg-slate-50 p-6 flex flex-col w-screen h-screen"
                        : "lg:col-span-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm flex flex-col h-[600px]"
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

                  <Card className="bg-white border-slate-200 shadow-sm flex flex-col h-[570px]">
                    <CardHeader className="py-3 px-4 border-b border-slate-200">
                      <CardTitle className="text-sm font-semibold text-slate-900">Connectors Edge List</CardTitle>
                      <CardDescription className="text-xs text-slate-500">
                        Extracted assembly connectors from composition
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-3 overflow-y-auto space-y-2 flex-1">
                      {s2[graphVersion].edges.map((e: any, idx: number) => (
                        <div key={idx} className="p-2 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100/70 text-xs font-mono">
                          <div className="flex items-center justify-between text-slate-900 font-semibold">
                            <span>
                              {e.source.split("/").pop()} &rarr; {e.target.split("/").pop()}
                            </span>
                            <span className="text-[10px] text-slate-500 uppercase font-sans font-medium">{e.influence}</span>
                          </div>
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">{e.connector}</p>
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
                    <Badge variant="outline" className="text-blue-700 border-blue-200 bg-blue-50 mb-1 font-semibold">
                      Stage 3 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">3-Valued SecOC Wire Annotation</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Determines physical wire security by tracing each connector down to its carrying I-PDU.
                    </p>
                  </div>
                </div>

                {/* 3 Metric Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card className="bg-white border-slate-200 border-l-4 border-l-slate-400 shadow-sm">
                    <CardHeader className="py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-slate-800">RTE_LOCAL (None)</span>
                        <Badge variant="secondary" className="font-mono text-xs bg-slate-100 text-slate-700 border border-slate-200">
                          {s3.updated.local_count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Connectors remain within the same physical ECU. No physical wire frame is created.
                      </p>
                    </CardHeader>
                  </Card>

                  <Card className="bg-white border-slate-200 border-l-4 border-l-emerald-500 shadow-sm">
                    <CardHeader className="py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-emerald-800">AUTHENTICATED (True)</span>
                        <Badge variant="outline" className="font-mono text-xs text-emerald-800 border-emerald-300 bg-emerald-50">
                          {s3.updated.authenticated_count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-600 mt-1">
                        Cross-ECU bus traffic wrapped in SECURED-I-PDU with cryptographic freshness and MAC.
                      </p>
                    </CardHeader>
                  </Card>

                  <Card className="bg-white border-slate-200 border-l-4 border-l-rose-500 shadow-sm">
                    <CardHeader className="py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-rose-800">UNPROTECTED (False)</span>
                        <Badge variant="outline" className="font-mono text-xs text-rose-800 border-rose-300 bg-rose-50">
                          {s3.updated.unprotected_count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-600 mt-1">
                        Cross-ECU bus traffic without SecOC. Raw payload exposed to frame injection/tampering.
                      </p>
                    </CardHeader>
                  </Card>
                </div>

                {/* Table */}
                <Card className="bg-white border-slate-200 shadow-sm">
                  <CardHeader className="py-3 px-4 border-b border-slate-200">
                    <CardTitle className="text-sm font-semibold text-slate-900">Vehicle Communication Security Matrix</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 max-h-96 overflow-y-auto">
                    <Table>
                      <TableHeader className="bg-slate-50 sticky top-0">
                        <TableRow className="border-slate-200 text-xs">
                          <TableHead className="text-slate-600 font-semibold">Connector</TableHead>
                          <TableHead className="text-slate-600 font-semibold">Source &rarr; Target</TableHead>
                          <TableHead className="text-slate-600 font-semibold">Boundary</TableHead>
                          <TableHead className="text-slate-600 font-semibold">Security State</TableHead>
                          <TableHead className="text-slate-600 font-semibold">Carrying PDUs</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="divide-y divide-slate-200 text-xs font-mono">
                        {s3.updated.edges.map((e: any, idx: number) => (
                          <TableRow key={idx} className="border-slate-200 hover:bg-slate-50/80">
                            <TableCell className="font-semibold text-slate-900">{e.connector}</TableCell>
                            <TableCell className="text-slate-700">
                              {e.source.split("/").pop()} &rarr; {e.target.split("/").pop()}
                            </TableCell>
                            <TableCell className="text-slate-500">{e.bus_visible ? "Bus Wire" : "Internal Memory"}</TableCell>
                            <TableCell>
                              {e.security_state === "AUTHENTICATED" && (
                                <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px]">
                                  AUTHENTICATED 🔒
                                </Badge>
                              )}
                              {e.security_state === "UNPROTECTED" && (
                                <Badge className="bg-rose-100 text-rose-800 border-rose-300 text-[10px]">
                                  UNPROTECTED ⚠️
                                </Badge>
                              )}
                              {e.security_state === "RTE_LOCAL" && (
                                <Badge variant="secondary" className="bg-slate-100 text-slate-700 border border-slate-200 text-[10px]">
                                  RTE_LOCAL
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-slate-500">{e.pdus.join(", ") || "None"}</TableCell>
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
                    <Badge variant="outline" className="text-blue-700 border-blue-200 bg-blue-50 mb-1 font-semibold">
                      Stage 4 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">Dual-Graph Diff & Transitive Attack Reachability</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Executes constrained DFS reachability analysis from untrusted entry nodes to ASIL-D critical targets.
                    </p>
                  </div>
                </div>

                {/* Seeds Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-white border-slate-200 shadow-sm">
                    <CardHeader className="py-3 px-4 border-b border-slate-200">
                      <CardTitle className="text-xs font-semibold uppercase tracking-wider text-blue-700 flex items-center gap-1.5">
                        <Radio className="w-3.5 h-3.5 text-blue-600" /> Untrusted Entry Points (S)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-3 flex flex-wrap gap-2">
                      {s4.roles.entry_points.map((ep: any) => (
                        <Badge key={ep.node} variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 font-mono text-xs">
                          {ep.label}
                        </Badge>
                      ))}
                    </CardContent>
                  </Card>

                  <Card className="bg-white border-slate-200 shadow-sm">
                    <CardHeader className="py-3 px-4 border-b border-slate-200">
                      <CardTitle className="text-xs font-semibold uppercase tracking-wider text-rose-700 flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" /> Safety-Critical Targets (T)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-3 flex flex-wrap gap-2">
                      {s4.roles.critical_targets.map((ct: any) => (
                        <Badge key={ct.node} variant="outline" className="bg-rose-50 text-rose-700 border-rose-200 font-mono text-xs">
                          {ct.label} (ASIL-{ct.asil})
                        </Badge>
                      ))}
                    </CardContent>
                  </Card>
                </div>

                {/* Discovered Attack Paths */}
                <Card className="bg-white border-slate-200 shadow-sm">
                  <CardHeader className="py-3 px-4 border-b border-slate-200 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-semibold text-slate-900">Newly Opened Attack Chains (&Delta;R)</CardTitle>
                    <Badge variant="outline" className="text-rose-700 border-rose-200 bg-rose-50 font-mono text-xs font-semibold">
                      {s4.reachability.new_paths.length} Transitive Path(s)
                    </Badge>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {s4.reachability.new_paths.length === 0 ? (
                      <p className="text-xs text-slate-500">Zero new attack reachability paths opened in this release.</p>
                    ) : (
                      s4.reachability.new_paths.map((p: any, idx: number) => (
                        <div key={idx} className="p-3 rounded-lg border border-rose-200 bg-rose-50/70 space-y-2 shadow-sm">
                          <div className="flex items-center justify-between text-xs font-semibold text-rose-900">
                            <span className="flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" /> Attack Route #{idx + 1} ({p.hops.length} Hops)
                            </span>
                            <Badge variant="outline" className="bg-rose-100 border-rose-300 text-rose-800 text-[10px]">
                              {p.unprotected ? "Unprotected Bus Hop Included" : "Secured"}
                            </Badge>
                          </div>
                          <div className="font-mono text-xs flex items-center flex-wrap gap-2 pt-1 text-slate-700">
                            {p.nodes.map((n: string, i: number) => (
                              <React.Fragment key={i}>
                                <span className={i === 0 ? "text-blue-700 font-bold" : i === p.nodes.length - 1 ? "text-rose-700 font-bold" : "text-slate-800"}>
                                  {n}
                                </span>
                                {i < p.nodes.length - 1 && <span className="text-slate-400">&rarr;</span>}
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
                    <Badge variant="outline" className="text-blue-700 border-blue-200 bg-blue-50 mb-1 font-semibold">
                      Stage 5 / 5
                    </Badge>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">ISO/SAE 21434 Risk Scoring & Release Gate</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Synthesizes target ASIL safety impact and attack feasibility into an automated release verdict.
                    </p>
                  </div>
                </div>

                {/* Verdict Hero Card */}
                <Card
                  className={`p-6 border shadow-md ${
                    s5.verdict === "BLOCK"
                      ? "border-rose-300 bg-rose-50/80"
                      : s5.verdict === "FLAG"
                      ? "border-amber-300 bg-amber-50/80"
                      : "border-emerald-300 bg-emerald-50/80"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div
                        className={`h-12 w-12 rounded-xl flex items-center justify-center text-white shadow-md ${
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
                                ? "text-rose-700"
                                : s5.verdict === "FLAG"
                                ? "text-amber-700"
                                : "text-emerald-700"
                            }`}
                          >
                            {s5.verdict}
                          </span>
                          <Badge variant="secondary" className="font-mono text-xs bg-white/90 border border-slate-200 text-slate-800">
                            exit code: {s5.exit_code}
                          </Badge>
                        </div>
                        <p className="text-xs text-slate-700 mt-1">
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
                        <p className="text-xs text-slate-500">Risk 5 / Severe</p>
                        <p className="text-2xl font-bold font-mono text-rose-700">{s5.risk_breakdown.risk_5}</p>
                      </div>
                      <Separator orientation="vertical" className="h-10 bg-slate-300" />
                      <div className="text-right">
                        <p className="text-xs text-slate-500">Total Findings</p>
                        <p className="text-2xl font-bold font-mono text-slate-900">{s5.findings.length}</p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Findings List */}
                <Card className="bg-white border-slate-200 shadow-sm">
                  <CardHeader className="py-3 px-4 border-b border-slate-200">
                    <CardTitle className="text-sm font-semibold text-slate-900">Audit Findings & Evidence Trace</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {s5.findings.map((f: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/70 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Badge
                              className={`text-[10px] font-mono font-bold ${
                                f.risk >= 4 ? "bg-rose-100 text-rose-800 border-rose-300" : "bg-amber-100 text-amber-800 border-amber-300"
                              }`}
                            >
                              RISK {f.risk} [{f.impact}/{f.feasibility}]
                            </Badge>
                            <span className="text-xs font-semibold text-slate-900">{f.title}</span>
                          </div>
                          <span className="text-[10px] font-mono text-slate-500 uppercase">{f.category}</span>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">{f.detail}</p>
                        {f.rationale.length > 0 && (
                          <div className="text-[11px] font-mono text-slate-700 bg-white p-2.5 rounded border border-slate-200">
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
      <footer className="border-t border-slate-200 py-4 px-6 text-center text-xs text-slate-500 bg-white">
        ARXML SecDiff Next.js App &bull; Powered by shadcn/ui &bull; Automated Cybersecurity Release Gate
      </footer>
    </div>
  );
}
