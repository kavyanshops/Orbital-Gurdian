import { useState, useEffect } from "react";
import { Rocket, AlertTriangle, Check, Activity, Zap } from "lucide-react";

interface ConjunctionEvent {
    event_id: string;
    tca: string;
    miss_distance: number;
    probability: number;
    risk_level: string;
}

interface ManeuverPlan {
    event_id: string;
    status: string;
    delta_v_magnitude: number;
    primary_maneuver?: {
        delta_vx: number;
        delta_vy: number;
        delta_vz: number;
        epoch_mjd2000: number;
    };
}

export default function ManeuverOptimizer() {
    const [events, setEvents] = useState<ConjunctionEvent[]>([]);
    const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
    const [isPlanning, setIsPlanning] = useState(false);
    const [plan, setPlan] = useState<ManeuverPlan | null>(null);
    const [algorithm, setAlgorithm] = useState("MCTS");

    const API_URL = "http://localhost:8000/api";

    const fetchEvents = async () => {
        try {
            const res = await fetch(`${API_URL}/conjunctions`);
            if (res.ok) {
                setEvents(await res.json());
            }
        } catch (e) {
            console.error("Failed to fetch events", e);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    const handlePlan = async () => {
        if (!selectedEventId) return;
        setIsPlanning(true);
        setPlan(null);
        try {
            const res = await fetch(`${API_URL}/maneuvers/plan`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ event_id: selectedEventId, max_delta_v: 5.0 })
            });
            if (res.ok) {
                setPlan(await res.json());
            }
        } catch (e) {
            console.error("Planning failed", e);
        } finally {
            setIsPlanning(false);
        }
    };

    return (
        <div className="md:p-6 space-y-8 animate-in fade-in duration-500">

            {/* Header */}
            <div className="flex items-center gap-4 bg-orange-950/20 border border-orange-500/20 p-6 rounded-xl">
                <div className="p-3 rounded-full bg-orange-500/20 text-orange-400">
                    <Rocket className="w-6 h-6" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Autonomous Maneuver Planning</h2>
                    <p className="text-xs text-slate-400">Select a high-risk event to generate optimal avoidance trajectories.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Left Column: Event Selection */}
                <div className="lg:col-span-1 space-y-4">
                    <h3 className="font-semibold text-slate-300 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" /> Active Threats
                    </h3>
                    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
                        {events.length === 0 ? (
                            <div className="p-8 text-center border border-white/10 rounded-xl bg-white/5 text-muted-foreground text-sm">
                                No active threats detected. Run screening first.
                            </div>
                        ) : (
                            events.map(evt => (
                                <button
                                    key={evt.event_id}
                                    onClick={() => { setSelectedEventId(evt.event_id); setPlan(null); }}
                                    className={`w-full text-left p-4 rounded-xl border transition-all ${selectedEventId === evt.event_id
                                        ? 'bg-orange-500/10 border-orange-500 text-white shadow-[0_0_15px_-5px] shadow-orange-500/30'
                                        : 'bg-black/40 border-white/10 text-slate-400 hover:bg-white/5 hover:border-white/20'}`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${evt.risk_level === 'CRITICAL' ? 'bg-red-500 text-white' : 'bg-yellow-500/20 text-yellow-400'}`}>
                                            {evt.risk_level}
                                        </span>
                                        <span className="text-[10px] mono text-slate-500">{new Date(evt.tca).toLocaleTimeString()}</span>
                                    </div>
                                    <div className="font-mono text-sm mb-1">Miss Dist: {evt.miss_distance.toFixed(3)} km</div>
                                    <div className="text-xs">Prob: {evt.probability.toExponential(1)}</div>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Right Column: Planning & Results */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Algorithm Selection */}
                    <div className="bg-black/20 border border-white/10 p-6 rounded-xl">
                        <h3 className="font-semibold text-slate-300 mb-4">Optimization Strategy</h3>
                        <div className="grid grid-cols-3 gap-4">
                            {['MCTS', 'PPO', 'CEM'].map(algo => (
                                <button
                                    key={algo}
                                    onClick={() => setAlgorithm(algo)}
                                    className={`p-3 rounded-lg border text-sm font-medium transition-colors ${algorithm === algo
                                        ? 'bg-orange-500/20 border-orange-500 text-orange-400'
                                        : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'}`}
                                >
                                    {algo} Agent
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Action Area */}
                    <div className="flex justify-end">
                        <button
                            onClick={handlePlan}
                            disabled={!selectedEventId || isPlanning}
                            className="px-8 py-3 bg-gradient-to-r from-orange-500 to-red-600 rounded-lg text-white font-bold shadow-lg shadow-orange-900/20 hover:scale-105 transition-all disabled:opacity-50 disabled:scale-100 flex items-center gap-2"
                        >
                            {isPlanning ? <Activity className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                            {isPlanning ? "Maneuver Planning in Progress..." : "Generate Optimal Maneuver"}
                        </button>
                    </div>

                    {/* Results Display */}
                    {plan && (
                        <div className="animate-in slide-in-from-bottom-4 duration-500">
                            <div className="bg-gradient-to-br from-green-950/30 to-black border border-green-500/30 rounded-xl overflow-hidden">
                                <div className="p-4 bg-green-500/10 border-b border-green-500/20 flex justify-between items-center">
                                    <h3 className="font-bold text-green-400 flex items-center gap-2">
                                        <Check className="w-5 h-5" /> Optimization Complete
                                    </h3>
                                    <span className="text-xs text-green-300/70 font-mono">ID: {plan.event_id.substring(0, 8)}...</span>
                                </div>
                                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div>
                                        <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Required Delta-V</div>
                                        <div className="text-4xl font-bold text-white mb-1">{plan.delta_v_magnitude.toFixed(4)} <span className="text-lg text-slate-500">m/s</span></div>
                                        <div className="text-xs text-slate-500">Fuel efficient trajectory found</div>
                                    </div>

                                    {plan.primary_maneuver && (
                                        <div className="space-y-2">
                                            <div className="text-slate-400 text-xs uppercase tracking-wider">Thrust Vector (ECI)</div>
                                            <div className="grid grid-cols-3 gap-2">
                                                <div className="p-2 bg-black/40 rounded border border-white/10 text-center">
                                                    <div className="text-[10px] text-slate-500">X</div>
                                                    <div className="font-mono text-sm">{plan.primary_maneuver.delta_vx.toFixed(3)}</div>
                                                </div>
                                                <div className="p-2 bg-black/40 rounded border border-white/10 text-center">
                                                    <div className="text-[10px] text-slate-500">Y</div>
                                                    <div className="font-mono text-sm">{plan.primary_maneuver.delta_vy.toFixed(3)}</div>
                                                </div>
                                                <div className="p-2 bg-black/40 rounded border border-white/10 text-center">
                                                    <div className="text-[10px] text-slate-500">Z</div>
                                                    <div className="font-mono text-sm">{plan.primary_maneuver.delta_vz.toFixed(3)}</div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                                <div className="p-4 bg-white/5 border-t border-white/10 flex justify-end gap-2">
                                    <button className="px-4 py-2 rounded-lg border border-white/10 text-sm hover:bg-white/5 text-slate-300">Simulate</button>
                                    <button className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-bold shadow-lg shadow-green-900/20">Execute Maneuver</button>
                                </div>
                            </div>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
