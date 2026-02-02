import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Search, Rocket, Microscope, ArrowRight, Satellite, TriangleAlert, RefreshCw, Eye } from "lucide-react";

import RealTimeDashboard from "./RealTimeDashboard";
import ManeuverOptimizer from "./ManeuverOptimizer";

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState("conjunction");
    const [satelliteTle, setSatelliteTle] = useState("");
    const [debrisTles, setDebrisTles] = useState("");
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [showManualInput, setShowManualInput] = useState(false);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    // Auto-fetch and Auto-analyze on Mount
    useEffect(() => {
        if (activeTab === 'conjunction' && !results && !isAnalyzing) {
            fetchAndAnalyze();
        }
    }, [activeTab]);

    const fetchAndAnalyze = async () => {
        setIsAnalyzing(true);
        try {
            // 1. Fetch Live Data
            const res = await fetch("http://localhost:5050/api/live-satellites");
            if (!res.ok) throw new Error("Failed to fetch live data");
            const data = await res.json();

            // 2. Format for Analysis
            const primarySat = data.satellite;
            const primaryTle = `${primarySat.name}\n${primarySat.line1}\n${primarySat.line2}`;

            const debrisObjects = data.debris.filter((d: any) => d.type === 'debris');
            const debrisTleString = debrisObjects.map((d: any) => `${d.name}\n${d.line1}\n${d.line2}`).join('\n');

            setSatelliteTle(primaryTle);
            setDebrisTles(debrisTleString);

            // 3. Trigger Analysis
            const analysisRes = await fetch("http://localhost:5050/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ satellite_tle: primaryTle, debris_tles: debrisTleString }),
            });
            const analysisData = await analysisRes.json();

            setResults(analysisData);
            setLastUpdated(new Date());

        } catch (e) {
            console.error("Auto-analysis failed", e);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const runManualAnalysis = async () => {
        setIsAnalyzing(true);
        try {
            const response = await fetch("http://localhost:5050/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ satellite_tle: satelliteTle, debris_tles: debrisTles }),
            });
            const data = await response.json();
            setResults(data);
            setLastUpdated(new Date());
        } catch (e) {
            console.error("Analysis failed", e);
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="w-full mt-8">
            {/* Tabs Header */}
            <div className="flex border-b border-border mb-6 overflow-x-auto whitespace-nowrap scrollbar-hide">
                <button
                    onClick={() => setActiveTab("conjunction")}
                    className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 flex-shrink-0 ${activeTab === "conjunction"
                        ? "border-cyan-400 text-cyan-400"
                        : "border-transparent text-muted-foreground hover:text-white"
                        }`}
                >
                    <Search className="w-4 h-4" /> Conjunction Screening
                </button>
                <button
                    onClick={() => setActiveTab("optical")}
                    className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 flex-shrink-0 ${activeTab === "optical"
                        ? "border-purple-400 text-purple-400"
                        : "border-transparent text-muted-foreground hover:text-white"
                        }`}
                >
                    <Microscope className="w-4 h-4" /> Optical Detection
                </button>
                <button
                    onClick={() => setActiveTab("maneuver")}
                    className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 flex-shrink-0 ${activeTab === "maneuver"
                        ? "border-orange-400 text-orange-400"
                        : "border-transparent text-muted-foreground hover:text-white"
                        }`}
                >
                    <Rocket className="w-4 h-4" /> Maneuver Optimization
                </button>
            </div>

            {/* Real-Time Tab */}
            {activeTab === "realtime" && <RealTimeDashboard />}

            {/* Conjunction Tab */}
            {activeTab === "conjunction" && (
                <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">

                    {/* Header / Controls */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/50 p-6 rounded-xl border border-white/10 backdrop-blur-md">
                        <div className="flex items-center gap-4">
                            <div className={`w-3 h-3 rounded-full shadow-[0_0_10px] ${isAnalyzing ? 'bg-yellow-400 shadow-yellow-400/50 animate-bounce' : 'bg-green-500 shadow-green-500/50 animate-pulse'}`}></div>
                            <div>
                                <h3 className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 text-xl">Automated Collision Monitoring</h3>
                                <p className="text-xs text-slate-400">
                                    {lastUpdated ? `Last scan: ${lastUpdated.toLocaleTimeString()}` : "Initializing system..."}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 w-full md:w-auto">
                            <button
                                onClick={fetchAndAnalyze}
                                disabled={isAnalyzing}
                                className="p-2 rounded-lg bg-white/5 text-white hover:bg-white/10 border border-white/10 disabled:opacity-50 transition-colors"
                                title="Force Rescan"
                            >
                                <RefreshCw className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
                            </button>
                            <button
                                onClick={() => setShowManualInput(!showManualInput)}
                                className="text-xs px-3 py-1.5 rounded-full border border-white/10 text-slate-300 hover:text-white hover:bg-white/5 transition-colors whitespace-nowrap"
                            >
                                {showManualInput ? "Hide Manual Input" : "Show Manual Input"}
                            </button>
                        </div>
                    </div>

                    {/* Manual Input Section (Conditional) */}
                    {showManualInput && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 rounded-xl bg-black/20 border border-dashed border-border mb-6">
                            <div className="p-4 rounded-xl border border-border bg-card">
                                <h3 className="text-sm font-semibold mb-2 text-cyan-400">Primary Satellite TLE</h3>
                                <textarea
                                    value={satelliteTle}
                                    onChange={(e) => setSatelliteTle(e.target.value)}
                                    className="w-full h-24 bg-black/50 border border-input rounded-lg p-2 text-[10px] font-mono text-muted-foreground outline-none resize-none"
                                />
                            </div>
                            <div className="p-4 rounded-xl border border-border bg-card">
                                <h3 className="text-sm font-semibold mb-2 text-red-400">Debris TLEs</h3>
                                <textarea
                                    value={debrisTles}
                                    onChange={(e) => setDebrisTles(e.target.value)}
                                    className="w-full h-24 bg-black/50 border border-input rounded-lg p-2 text-[10px] font-mono text-muted-foreground outline-none resize-none"
                                />
                            </div>
                            <div className="col-span-full flex justify-end">
                                <button onClick={runManualAnalysis} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-bold">Run Manual Analysis</button>
                            </div>
                        </div>
                    )}

                    {/* System Status / Results */}
                    {!results && isAnalyzing && (
                        <div className="flex flex-col items-center justify-center py-20 text-center">
                            <RefreshCw className="w-12 h-12 text-cyan-400 animate-spin mb-4" />
                            <h2 className="text-2xl font-bold">Scanning Space Domain...</h2>
                            <p className="text-muted-foreground">Fetching telemetry and propagating orbits.</p>
                        </div>
                    )}

                    {results && (
                        <div className="space-y-6">
                            {/* Main Status Cards */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                {/* Overall Status */}
                                <div className={`p-6 rounded-2xl border ${results.data?.overall_status === 'WARNINGS_PRESENT' ? 'bg-red-950/30 border-red-500/50' : 'bg-green-950/30 border-green-500/50'} flex flex-col items-center justify-center text-center shadow-lg relative overflow-hidden group`}>
                                    <div className={`absolute inset-0 bg-gradient-to-br ${results.data?.overall_status === 'WARNINGS_PRESENT' ? 'from-red-500/10' : 'from-green-500/10'} to-transparent opacity-0 group-hover:opacity-100 transition-opacity`}></div>
                                    {results.data?.overall_status === 'WARNINGS_PRESENT' ? <AlertCircle className="w-16 h-16 text-red-500 mb-4" /> : <CheckCircle className="w-16 h-16 text-green-500 mb-4" />}
                                    <h2 className="text-3xl font-bold text-white mb-1">
                                        {results.data?.overall_status === 'WARNINGS_PRESENT' ? 'WARNING' : 'SAFE'}
                                    </h2>
                                    <p className={`text-sm font-medium ${results.data?.overall_status === 'WARNINGS_PRESENT' ? 'text-red-400' : 'text-green-400'}`}>
                                        SYSTEM STATUS
                                    </p>
                                </div>

                                <div className="p-6 rounded-2xl border border-white/10 bg-card/50 flex flex-col justify-center backdrop-blur-sm">
                                    <div className="flex items-center gap-3 mb-4 text-cyan-400">
                                        <Satellite className="w-6 h-6" />
                                        <span className="text-sm font-bold tracking-wider uppercase">Primary Asset</span>
                                    </div>
                                    <div className="text-2xl font-bold text-white mb-1 truncate">{results.data?.satellite_name || "Unknown"}</div>
                                    <div className="text-sm text-slate-400">Cat ID: {results.data?.satellite_catalog_number}</div>
                                </div>

                                {/* Threat Summary */}
                                <div className="p-6 rounded-2xl border border-white/10 bg-card/50 flex flex-col justify-center backdrop-blur-sm">
                                    <div className="flex items-center gap-3 mb-4 text-orange-400">
                                        <Eye className="w-6 h-6" />
                                        <span className="text-sm font-bold tracking-wider uppercase">Threat Screening</span>
                                    </div>
                                    <div className="flex justify-between items-end">
                                        <div>
                                            <div className="text-2xl font-bold text-white">{results.data?.debris_analyzed}</div>
                                            <div className="text-xs text-slate-400">Objects Analyzed</div>
                                        </div>
                                        <div className="text-right">
                                            <div className={`text-2xl font-bold ${results.data?.warnings_count > 0 ? 'text-red-500' : 'text-green-500'}`}>
                                                {results.data?.warnings_count}
                                            </div>
                                            <div className="text-xs text-slate-400">Active Warnings</div>
                                        </div>
                                    </div>
                                </div>
                            </div>


                            {/* Detailed Results Table */}
                            {results.data?.results && results.data.results.length > 0 && (
                                <div className="rounded-xl border border-white/10 overflow-hidden bg-black/40 backdrop-blur-sm">
                                    <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex justify-between items-center">
                                        <h3 className="font-semibold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">Proximity Alerts</h3>
                                        <span className="text-xs text-slate-400">Sorted by urgency</span>
                                    </div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm text-left whitespace-nowrap">
                                            <thead className="bg-white/5 text-slate-300 uppercase text-xs font-semibold tracking-wider">
                                                <tr>
                                                    <th className="px-6 py-4">Threat Level</th>
                                                    <th className="px-6 py-4">Object ID</th>
                                                    <th className="px-6 py-4">Miss Distance</th>
                                                    <th className="px-6 py-4">Time to Approach</th>
                                                    <th className="px-6 py-4">Action</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/10">
                                                {results.data.results.filter((r: any) => r.status !== 'FILTERED').map((res: any, idx: number) => (
                                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                                        <td className="px-6 py-4">
                                                            {res.status === 'WARNING' ? (
                                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/20 text-red-400 text-xs font-bold border border-red-500/30">
                                                                    <TriangleAlert className="w-3 h-3" /> CRITICAL
                                                                </span>
                                                            ) : (
                                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-bold border border-green-500/30">
                                                                    <CheckCircle className="w-3 h-3" /> MONITORING
                                                                </span>
                                                            )}
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <div className="font-mono text-white">{res.debris_id}</div>
                                                            <div className="text-xs text-slate-400">ID: {res.catalog_number}</div>
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <div className={`font-mono font-bold ${res.min_distance_km < 10 ? 'text-red-400' : 'text-slate-300'}`}>
                                                                {res.min_distance_km.toFixed(2)} km
                                                            </div>
                                                        </td>
                                                        <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                                                            {res.closest_approach_time || '-'}
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            {res.status === 'WARNING' && (
                                                                <button className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1 underline decoration-dotted">
                                                                    View Options <ArrowRight className="w-3 h-3" />
                                                                </button>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                                {results.data.results.filter((r: any) => r.status !== 'FILTERED').length === 0 && (
                                                    <tr>
                                                        <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">
                                                            No proximity events detected within screening volume.
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Maneuver Tab */}
            {activeTab === "maneuver" && <ManeuverOptimizer />}

            {/* Optical Tab Placeholder */}
            {activeTab === "optical" && (
                <div className="p-12 text-center border border-dashed border-border rounded-xl bg-black/20">
                    <Microscope className="w-12 h-12 text-purple-400 mx-auto mb-4" />
                    <h3 className="text-2xl font-bold mb-2">Optical Detection System</h3>
                    <p className="text-muted-foreground mb-6">AI-powered imagery analysis for debris identification.</p>
                    <a href="http://localhost:5050/optical" target="_blank" className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-full inline-block">
                        Launch Optical Module ↗
                    </a>
                </div>
            )}

        </div>
    );
}
